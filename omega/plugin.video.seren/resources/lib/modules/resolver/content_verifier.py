"""
Content Verification Module

Verifies that resolved sources (torrent AND cloud) actually match the expected
Movie or TV Show episode metadata before playback begins.

Torrent verification:
  - If the content doesn't match, the source is skipped and the next one is tried.
  - After a configurable number of consecutive mismatches (default 3), the torrent/scraper
    cache is cleared and a full rescrape is triggered automatically.

Cloud verification (bulk cleanup):
  - If a cloud source doesn't match, ALL remaining cloud sources in the source list
    are verified against expected metadata. Every mismatched cloud item is auto-deleted
    from the debrid cloud (PM/RD/AD/TB) in a single pass.
  - Torrent sources whose release_title matches a deleted cloud file (or also fails
    verification) have their hashes invalidated from the debrid cache, preventing stale
    "cached" entries from reappearing on the rescrape.
  - A single Kodi notification summarizes the total number of deleted items.
  - The local cache is cleared and a full rescrape is triggered immediately.

Integration points:
  - Resolver.resolve_multiple_until_valid_link() (autoplay)
  - ResolverWindow._resolve_source() (visible resolver)
  - Router getSources action (rescrape trigger)
"""

import re

import xbmcgui

from resources.lib.common import source_utils
from resources.lib.modules.globals import g


class ContentVerifier:
    """
    Tracks content mismatches during resolution and verifies release titles
    against the expected item metadata.

    Usage:
        verifier = ContentVerifier(item_information, sources)
        ...
        for source in sources:
            stream_link, release_title = resolver.resolve_single_source(...)
            if stream_link and not verifier.verify(source, release_title):
                stream_link = None  # skip this source
                if verifier.should_rescrape():
                    break  # signal caller to rescrape
    """

    def __init__(self, item_information, sources=None):
        self.item_information = item_information
        self.info = item_information.get("info", {})
        self.media_type = self.info.get("mediatype", "")
        self.enabled = g.get_bool_setting("general.contentVerify", True)
        self.cloud_enabled = g.get_bool_setting("general.cloudContentVerify", True)
        self.max_mismatches = g.get_int_setting("general.contentVerifyMaxMismatch", 3)
        self.mismatch_count = 0
        self._rescrape_needed = False
        self._sources = sources or []
        self._bulk_cleaned = False

    @property
    def rescrape_needed(self):
        """True if mismatch threshold was reached and a rescrape should happen."""
        return self._rescrape_needed

    def verify(self, source, release_title=None):
        """
        Verify that a source matches the expected content.

        Checks both torrent and cloud source types.
        Returns True if the source passes verification or verification is disabled.
        Returns False if the source is a content mismatch.

        For cloud mismatches: auto-deletes from debrid cloud, shows notification,
        and immediately flags for rescrape.

        :param source: The source dict being resolved
        :param release_title: The release title returned by the resolver (may differ
                              from source['release_title'] for pack files)
        :return: True if content matches or verification is skipped, False if mismatch
        """
        source_type = source.get("type", "")

        # Determine if this source type should be verified
        if source_type == "torrent" and not self.enabled:
            return True
        if source_type == "cloud" and not self.cloud_enabled:
            return True
        if source_type not in ("torrent", "cloud"):
            return True  # hosters/direct/adaptive — skip verification

        # Use the resolver-returned release title if available, else fall back to source
        title_to_check = release_title or source.get("release_title", "")
        if not title_to_check:
            return True  # Can't verify without a title, allow through

        if self.media_type == "movie":
            matched = self._verify_movie(title_to_check)
        elif self.media_type == "episode":
            matched = self._verify_episode(title_to_check, source)
        else:
            return True  # Unknown media type, skip verification

        if matched:
            return True

        # ── Mismatch handling ──────────────────────────────────────────────

        if source_type == "cloud":
            # Cloud mismatch — delete from debrid cloud + immediate rescrape
            self._handle_cloud_mismatch(source, title_to_check)
            self._rescrape_needed = True
            g.log(
                "Cloud content verification: Mismatch triggers cache clear + rescrape",
                "warning",
            )
        else:
            # Torrent mismatch — count toward threshold
            self.mismatch_count += 1
            g.log(
                f"Content verification MISMATCH #{self.mismatch_count}/{self.max_mismatches}: "
                f"'{title_to_check}' does not match expected "
                f"{self._expected_description()}",
                "warning",
            )
            if self.mismatch_count >= self.max_mismatches:
                self._rescrape_needed = True
                g.log(
                    f"Content verification: {self.max_mismatches} mismatches reached — "
                    f"will clear cache and rescrape",
                    "warning",
                )

        return False

    def should_rescrape(self):
        """Check if mismatch threshold has been reached."""
        return self._rescrape_needed

    # ── Cloud mismatch handling ────────────────────────────────────────────

    def _handle_cloud_mismatch(self, source, title_to_check):
        """
        Handle a cloud source content mismatch with bulk cleanup:
        1. Delete the triggering mismatched item from the debrid cloud
        2. Scan ALL remaining cloud sources in the source list — verify each
           using its release_title and delete every one that also fails
        3. Invalidate debrid cache entries for torrent hashes whose release_title
           matches any deleted cloud source (stale cache cleanup)
        4. Show a single Kodi notification with total deleted count
        """
        debrid_provider = source.get("debrid_provider", "unknown")
        g.log(
            f"Cloud content verification MISMATCH: "
            f"'{title_to_check}' from {debrid_provider} does not match expected "
            f"{self._expected_description()} — starting bulk cloud cleanup",
            "warning",
        )

        if self._bulk_cleaned:
            # Already ran bulk cleanup this session, don't repeat
            return

        self._bulk_cleaned = True
        deleted_count = 0
        deleted_titles = set()

        # ── 1. Delete the triggering source ────────────────────────────────
        if self._delete_single_cloud_source(source):
            deleted_count += 1
            deleted_titles.add(source.get("release_title", ""))

        # ── 2. Bulk-verify and delete all other mismatched cloud sources ───
        for other_source in self._sources:
            if other_source is source:
                continue  # already handled above
            if other_source.get("type") != "cloud":
                continue
            if not other_source.get("_cloud_delete_info"):
                continue

            other_title = other_source.get("release_title", "")
            if not other_title:
                continue

            if not self._verify_title_only(other_title, other_source):
                if self._delete_single_cloud_source(other_source):
                    deleted_count += 1
                    deleted_titles.add(other_title)

        # ── 3. Stale cache cleanup — invalidate debrid cache hashes ────────
        # Find torrent sources whose release_title matches a deleted cloud
        # file. These torrents likely resolve to the same wrong content, so
        # clear their debrid cache entries to prevent them from being
        # pre-marked as "cached" on the rescrape.
        # Only runs if torrent content verification is enabled — respects the
        # user's choice to opt out of torrent-level title matching.
        stale_hashes = []
        if self.enabled:
            for src in self._sources:
                if src.get("type") != "torrent":
                    continue
                src_hash = src.get("hash", "")
                src_title = src.get("release_title", "")
                if not src_hash or not src_title:
                    continue
                if src_title in deleted_titles:
                    stale_hashes.append(src_hash)
                elif not self._verify_title_only(src_title, src):
                    # Also catch torrents that fail verification even if their
                    # exact title wasn't in a deleted cloud file
                    stale_hashes.append(src_hash)

        if stale_hashes:
            try:
                from resources.lib.database.debridCache import DebridCache
                DebridCache().invalidate_hashes(stale_hashes)
                g.log(
                    f"Cloud bulk cleanup: Invalidated {len(stale_hashes)} stale "
                    f"debrid cache hashes",
                    "info",
                )
            except Exception as e:
                g.log(f"Cloud bulk cleanup: Cache invalidation error: {e}", "warning")

        # ── 4. Single notification summarizing all deletions ───────────────
        if deleted_count > 0:
            g.log(
                f"Cloud bulk cleanup complete: Deleted {deleted_count} mismatched "
                f"cloud items, invalidated {len(stale_hashes)} debrid cache hashes",
                "info",
            )
            xbmcgui.Dialog().notification(
                g.ADDON_NAME,
                f"Cleaned {deleted_count} mismatched cloud file{'s' if deleted_count != 1 else ''}",
                time=4000,
            )

    def _delete_single_cloud_source(self, source):
        """Delete a single cloud source from its debrid service.

        Returns True if deletion succeeded, False otherwise.
        """
        delete_info = source.get("_cloud_delete_info")
        if not delete_info:
            g.log(
                f"Cloud verification: No delete info for "
                f"{source.get('debrid_provider', '?')} source — skipping",
                "warning",
            )
            return False

        service = delete_info.get("service", "")
        method = delete_info.get("method", "")
        item_id = delete_info.get("id", "")

        if not service or not method or not item_id:
            g.log(
                f"Cloud verification: Incomplete delete info "
                f"({service}/{method}/{item_id}) — skipping",
                "warning",
            )
            return False

        try:
            debrid_module = self._get_debrid_module(service)
            if debrid_module and hasattr(debrid_module, method):
                getattr(debrid_module, method)(item_id)
                g.log(
                    f"Cloud bulk cleanup: Deleted '{source.get('release_title', 'N/A')}' "
                    f"from {service} (method={method}, id={item_id})",
                    "info",
                )
                return True
            else:
                g.log(
                    f"Cloud verification: Delete method '{method}' not found on {service}",
                    "error",
                )
        except Exception as e:
            g.log(
                f"Cloud verification: Failed to delete from {service}: {e}",
                "error",
            )
        return False

    def _verify_title_only(self, release_title, source):
        """Verify a release title without needing a resolved stream link.

        Used for bulk cloud cleanup — checks the source's own release_title
        against expected metadata, same as verify() but without requiring
        the resolver to have run on this source.
        """
        if not release_title:
            return True  # Can't verify, allow through

        if self.media_type == "movie":
            return self._verify_movie(release_title)
        elif self.media_type == "episode":
            return self._verify_episode(release_title, source)
        return True

    @staticmethod
    def _get_debrid_module(service):
        """Lazy-load the appropriate debrid module by service name."""
        if service == "real_debrid":
            from resources.lib.debrid.real_debrid import RealDebrid
            return RealDebrid()
        elif service == "premiumize":
            from resources.lib.debrid.premiumize import Premiumize
            return Premiumize()
        elif service == "all_debrid":
            from resources.lib.debrid.all_debrid import AllDebrid
            return AllDebrid()
        elif service == "torbox":
            from resources.lib.debrid.torbox import TorBox
            return TorBox()
        return None

    # ── Movie verification ─────────────────────────────────────────────────

    def _verify_movie(self, release_title):
        """
        Verify a movie source. Checks that the release title contains the
        movie title and year, and does NOT look like a TV episode.
        """
        title = self.info.get("originaltitle", self.info.get("title", ""))
        year = str(self.info.get("year", ""))
        if not title:
            return True  # No title metadata, can't verify

        simple_info = {"year": year, "title": title}
        clean_release = source_utils.clean_title(release_title)
        clean_movie = source_utils.clean_title(title)

        # Quick check: does the release title contain the movie title?
        if clean_movie and clean_movie in clean_release:
            # Also verify it doesn't look like a random TV episode
            # First strip codec identifiers that look like episode numbers
            # (e.g. "x265", "x264", "h265", "h264" match the NxN pattern)
            codec_stripped = re.sub(r'\b[xh]\.?26[0-9]\b', '', clean_release)
            if source_utils.check_episode_number_match(codec_stripped):
                # Has S01E01-style markers — might be a TV show, not a movie
                # Unless "season" is part of the movie title itself
                if "season" not in clean_movie:
                    g.log(
                        f"Content verification: '{release_title}' contains movie title "
                        f"but has episode markers — likely wrong content",
                        "debug",
                    )
                    return False
            return True

        # Use the more thorough filter_movie_title check
        # Strip codec identifiers (x265/x264/h265 etc.) that trigger false
        # episode pattern matches inside filter_movie_title's own checks
        codec_safe_release = re.sub(r'[xXhH]\.?26[0-9]', '', release_title)
        if source_utils.filter_movie_title(
            release_title, codec_safe_release, title, simple_info
        ):
            return True

        # Try with original title variations (broken apostrophes etc.)
        for broken in (1, 2):
            alt_title = source_utils.clean_title(title, broken=broken)
            if alt_title and alt_title in clean_release:
                return True

        return False

    # ── Episode verification ───────────────────────────────────────────────

    def _verify_episode(self, release_title, source):
        """
        Verify a TV episode source. Handles three cases:
        1. Single episode — must match show title + SxxExx
        2. Season pack — must match show title + season number
        3. Show pack — must match show title + pack keywords

        For cloud sources, the `package` field may not be set — falls back to
        the episode regex which handles single episodes, season packs, and
        episode title matching.
        """
        show_title = self.info.get("tvshowtitle", "")
        if not show_title:
            return True  # No show title metadata, can't verify

        clean_release = source_utils.clean_title(release_title)
        clean_show = source_utils.clean_title(show_title)

        # Step 1: Show title must be present in release title
        if clean_show and clean_show not in clean_release:
            # Try alias matching
            aliases = self.info.get("aliases", [])
            alias_found = False
            for alias in aliases:
                if source_utils.clean_title(alias) in clean_release:
                    alias_found = True
                    break
            if not alias_found:
                return False

        # Step 2: Verify season/episode specifics based on package type
        package = source.get("package", "")
        season = str(self.info.get("season", ""))
        episode = str(self.info.get("episode", ""))

        # Override package type if release title clearly contains multiple
        # seasons (e.g. "S01-S02-S03-S04-S05", "S01 S05", "Season 1-5").
        # Scrapers sometimes misclassify these as "single".
        season_markers = re.findall(r"s(\d+)", clean_release)
        if len(season_markers) >= 2:
            package = "show"
        elif package == "single" and re.search(
            r"(?:complete|collection|series|all.?seasons|full.?series|boxset)", clean_release
        ):
            package = "show"

        if package == "single":
            return self._verify_single_episode(clean_release, season, episode)
        elif package == "season":
            return self._verify_season_pack(clean_release, season)
        elif package == "show":
            return self._verify_show_pack(clean_release, season)

        # No package type (cloud sources) or unknown — use full episode regex fallback
        # This handles all formats: single episodes, season packs, episode title matching
        return self._verify_episode_regex(clean_release)

    def _verify_single_episode(self, clean_release, season, episode):
        """Verify a single episode torrent has correct S/E numbers.

        Checks both the Trakt season/episode (e.g. S01E32) and the
        cour-corrected alternative season/episode (e.g. S02E04) that Seren's
        anime enrichment stores in info['alternative_season'] /
        info['alternative_episode'].  This prevents correct fansub releases
        like '[SubsPlease] Sousou no Frieren S2 - 04' from being rejected when
        Trakt numbers them as S01E32.
        """
        s = season
        e = episode

        # Common SxxExx patterns against Trakt season/episode
        patterns = [
            rf"s0?{re.escape(s)} ?e0?{re.escape(e)}(?:e\d+)?(?:\s|$|\.)",
            rf"season ?0?{re.escape(s)} ?(?:episode|ep) ?0?{re.escape(e)}",
            rf" 0?{re.escape(s)} ?x ?0?{re.escape(e)} ",
        ]

        for pattern in patterns:
            if re.search(pattern, clean_release):
                return True

        # ── Cour-corrected alternative season/episode (anime multi-cour) ──
        # Seren's anime enrichment computes cour-corrected numbers and stores
        # them in info['alternative_season'] / info['alternative_episode'].
        # e.g. Trakt S01E32 → alt S02E04 for Frieren 2nd cour.
        # Fansub releases use the alt numbers, so we must accept them here.
        alt_s = str(self.info.get("alternative_season", "") or "")
        alt_e = str(self.info.get("alternative_episode", "") or "")
        if alt_s and alt_e and (alt_s != season or alt_e != episode):
            alt_e_int = str(int(alt_e)) if alt_e.isdigit() else alt_e

            # SxxExx patterns against alt season/episode
            alt_sxe_patterns = [
                rf"s0?{re.escape(alt_s)} ?e0?{re.escape(alt_e)}(?:e\d+)?(?:\s|$|\.)",
                rf"season ?0?{re.escape(alt_s)} ?(?:episode|ep) ?0?{re.escape(alt_e)}",
                rf" 0?{re.escape(alt_s)} ?x ?0?{re.escape(alt_e)} ",
            ]
            for pattern in alt_sxe_patterns:
                if re.search(pattern, clean_release):
                    return True

            # Fansub-style pattern: "S{n}" season tag present AND standalone ep number.
            # Matches e.g. '[SubsPlease] Sousou no Frieren S2 - 04 (1080p)'
            # which clean_title turns into 'sousou no frieren s2 04 1080p'.
            has_ep_num = bool(
                re.search(
                    rf"(?:^|\s)0*{re.escape(alt_e_int)}(?:\s|v\d|$)",
                    clean_release,
                )
            )
            has_season_tag = bool(
                re.search(rf"\bs0?{re.escape(alt_s)}\b", clean_release)
            )
            if has_season_tag and has_ep_num:
                return True

            # Ordinal/cardinal season label + standalone ep number.
            # Matches '[Erai-raws] Sousou no Frieren 2nd Season - 04'
            # → clean: 'erai raws sousou no frieren 2nd season 04 1080p'
            _ord = {1: "st", 2: "nd", 3: "rd"}
            _n = int(alt_s) if alt_s.isdigit() else 0
            _suf = _ord.get(_n % 10 if _n % 100 not in (11, 12, 13) else 0, "th")
            has_ordinal_season = bool(
                re.search(
                    rf"\b{re.escape(alt_s)}(?:{_suf})?\s*season|season\s*0?{re.escape(alt_s)}\b",
                    clean_release,
                )
            )
            if has_ordinal_season and has_ep_num:
                return True

        # Also accept if the full episode regex matches
        return self._verify_episode_regex(clean_release)

    def _verify_season_pack(self, clean_release, season):
        """Verify a season pack torrent has the correct season number.

        Also accepts the cour-corrected alternative season (e.g. Trakt season 1
        but release labelled S2 for a cour-split anime). The alt season is read
        directly from item_information['info'] which is populated by getSources.
        """
        s = season
        s2 = season.zfill(2)

        season_patterns = [
            f"s{s} ", f"s{s2} ", f"s{s}.", f"s{s2}.",
            f"season {s}", f"season {s2}",
            f"seasons", f"complete",
        ]

        for pattern in season_patterns:
            if pattern in clean_release:
                return True

        # Also check the cour-corrected alternative season if present
        alt_s = str(self.info.get("alternative_season", ""))
        if alt_s and alt_s != season:
            alt_s2 = alt_s.zfill(2)
            alt_patterns = [
                f"s{alt_s} ", f"s{alt_s2} ", f"s{alt_s}.", f"s{alt_s2}.",
                f"season {alt_s}", f"season {alt_s2}",
            ]
            for pattern in alt_patterns:
                if pattern in clean_release:
                    return True

        # Also accept show packs
        return self._verify_show_pack(clean_release, season)

    def _verify_show_pack(self, clean_release, season):
        """Verify a show/complete pack contains the right season range.

        Also handles ordinal and cardinal season labels from the cour-corrected
        alternative season (e.g. "2nd Season", "Season 2") which Erai-raws and
        similar fansubs use instead of SxxExx numbering.
        """
        pack_keywords = [
            "complete", "series", "collection", "boxset", "box set",
            "all seasons", "full series", "seasons",
        ]
        if any(kw in clean_release for kw in pack_keywords):
            return True

        # Check for season range that includes our season (e.g. "s01 s05")
        s = int(season) if season.isdigit() else 0
        season_range = re.findall(r"s(\d+)", clean_release)
        if len(season_range) >= 2:
            try:
                low = int(season_range[0])
                high = int(season_range[-1])
                if low <= s <= high:
                    return True
            except (ValueError, IndexError):
                pass

        # Check for ordinal/cardinal alt season label: "2nd Season", "Season 2",
        # "3rd Season", etc. (Erai-raws style) using the cour-corrected season.
        alt_s = str(self.info.get("alternative_season", ""))
        if alt_s and alt_s.isdigit():
            if re.search(
                rf"\b{alt_s}(?:st|nd|rd|th)?\s+season|season\s+0?{alt_s}(?!\d)",
                clean_release,
            ):
                return True

        return False

    def _verify_episode_regex(self, clean_release):
        """
        Use the existing full meta episode regex as a final fallback check.
        This handles edge cases like episode title matching.
        """
        try:
            regex = source_utils._full_meta_episode_regex(self.item_information)
            matches = regex.findall(clean_release)
            return len(matches) > 0
        except Exception:
            return True  # If regex fails, don't block playback

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _expected_description(self):
        """Human-readable description of what we expected to find."""
        if self.media_type == "movie":
            title = self.info.get("title", "Unknown")
            year = self.info.get("year", "")
            return f"movie: {title} ({year})"
        elif self.media_type == "episode":
            show = self.info.get("tvshowtitle", "Unknown")
            season = self.info.get("season", "?")
            episode = self.info.get("episode", "?")
            return f"episode: {show} S{str(season).zfill(2)}E{str(episode).zfill(2)}"
        return "unknown content"
