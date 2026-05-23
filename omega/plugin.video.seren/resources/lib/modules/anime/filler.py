"""Anime Filler Episode Detection — scrapes animefillerlist.com for filler data.

Returns per-episode filler/canon/mixed status based on show title.
Uses stdlib html.parser (no BeautifulSoup dependency).
Results cached in module-level dict per show slug.
"""

import re
from html.parser import HTMLParser

import requests

from resources.lib.modules.globals import g

FILLER_LIST_URL = "https://www.animefillerlist.com/shows"

# Session-level cache: {slug: [list of episode type strings]}
_filler_cache = {}


class _EpisodeListParser(HTMLParser):
    """Minimal parser to extract episode types from animefillerlist.com HTML.

    Matches Otaku's BeautifulSoup pattern: for each <tr> in the EpisodeList table,
    captures the text of the first <span> (the type indicator like "Filler", "Canon").
    """

    def __init__(self):
        super().__init__()
        self.results = []
        self._in_episode_table = False
        self._in_row = False
        self._in_span = False
        self._got_span_this_row = False
        self._current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and "EpisodeList" in attrs_dict.get("class", ""):
            self._in_episode_table = True
        if self._in_episode_table and tag == "tr":
            self._in_row = True
            self._got_span_this_row = False
        if self._in_row and tag == "span" and not self._got_span_this_row:
            self._in_span = True
            self._current_text = ""

    def handle_data(self, data):
        if self._in_span:
            self._current_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "span" and self._in_span:
            self._in_span = False
            self._got_span_this_row = True
            if self._current_text:
                self.results.append(self._current_text)
        if tag == "tr" and self._in_row:
            self._in_row = False
        if tag == "table" and self._in_episode_table:
            self._in_episode_table = False


def _title_to_slug(title):
    """Convert a show title to animefillerlist.com URL slug.

    Examples:
        "Naruto Shippuden" → "naruto-shippuden"
        "One Piece" → "one-piece"
        "Attack on Titan" → "attack-on-titan"
    """
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def get_filler_list(show_title):
    """Get filler episode list for a show by title.

    Args:
        show_title: English show title (e.g. "Naruto Shippuden")

    Returns:
        list of episode type strings in order, e.g.:
        ["Manga Canon", "Manga Canon", "Filler", "Mixed Canon/Filler", ...]
        Empty list if show not found or on error.
        Index 0 = episode 1, index 1 = episode 2, etc.
    """
    if not show_title:
        return []

    slug = _title_to_slug(show_title)

    # Check cache
    if slug in _filler_cache:
        return _filler_cache[slug]

    try:
        url = f"{FILLER_LIST_URL}/{slug}"
        response = requests.get(url, timeout=5, headers={"User-Agent": "Seren"})

        if not response.ok:
            g.log(f"Filler list: no data for '{show_title}' (slug={slug}, status={response.status_code})", "debug")
            _filler_cache[slug] = []
            return []

        parser = _EpisodeListParser()
        parser.feed(response.text)

        _filler_cache[slug] = parser.results
        if parser.results:
            filler_count = sum(1 for ep in parser.results if "filler" in ep.lower() and "canon" not in ep.lower())
            g.log(
                f"Filler list: '{show_title}' — {len(parser.results)} episodes, {filler_count} filler",
                "debug",
            )
        return parser.results

    except requests.RequestException as e:
        g.log(f"Filler list error for '{show_title}': {e}", "warning")
        _filler_cache[slug] = []
        return []


def is_filler(show_title, episode_number):
    """Check if a specific episode is filler.

    Args:
        show_title: English show title
        episode_number: Episode number (1-indexed)

    Returns:
        True if the episode is filler (not canon), False otherwise.
        Returns False if data is unavailable.
    """
    filler_list = get_filler_list(show_title)
    if not filler_list or episode_number < 1 or episode_number > len(filler_list):
        return False

    ep_type = filler_list[episode_number - 1].lower()
    return "filler" in ep_type and "canon" not in ep_type


def get_episode_type(show_title, episode_number):
    """Get the episode type string for a specific episode.

    Args:
        show_title: English show title
        episode_number: Episode number (1-indexed)

    Returns:
        Episode type string (e.g. "Filler", "Manga Canon", "Mixed Canon/Filler")
        or None if data unavailable.
    """
    filler_list = get_filler_list(show_title)
    if not filler_list or episode_number < 1 or episode_number > len(filler_list):
        return None

    return filler_list[episode_number - 1]


def invalidate_cache():
    """Clear the session-level filler cache."""
    global _filler_cache
    _filler_cache = {}
