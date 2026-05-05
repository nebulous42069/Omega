<p align="center">
  <img src="resources/media/icon.png" alt="MP3 Streams Echoed" width="200">
</p>

<h1>MP3 Streams Echoed</h1>

<p><strong>A modern, fully Python-3-native rebuild of the classic MP3 Streams Reloaded and its early-2000s codebase.</strong></p>

<p>
MP3 Streams Echoed preserves the original browsing and playback experience while replacing every internal subsystem with a stable, maintainable, Kodi-19+ architecture. What began as a compatibility repair became a full modernisation: all Python 2/3 bridge code removed, request and session handling rebuilt, long-standing crashes fixed, and the UX expanded with playlists, favourites, richer metadata, fanart, and visualizer control.
</p>

<p>
The addon behaves predictably across all routes, with hardened parsing, resilient caching, correct session lifecycle management, and consistent <code>InfoTagMusic</code> metadata throughout.
</p>

<hr>

<h2>Requirements</h2>

<ul>
  <li>Kodi 19 (Matrix) or later — tested on Kodi 21 (Omega)</li>
  <li>Python 3.8+</li>
  <li>Dependencies (auto-resolved from Kodi repo): <code>script.module.beautifulsoup4</code>, <code>script.module.requests</code>, <code>script.module.routing</code></li>
</ul>

<hr>

<h2>Installation</h2>

<p>Install from zip: <strong>Settings → Addons → Install from zip file</strong>, then select the downloaded zip. Kodi will detect the version and install dependencies automatically.</p>

<p>To build the zip yourself from the addon's parent directory:</p>

<pre>
cd /path/to/addon/parent
zip -qr plugin_audio_m3sr2019-2026.1.0.zip plugin.audio.m3sr2019
</pre>

<hr>

<h2>Architecture Notes</h2>

<ul>
  <li><strong>Logging:</strong> <code>xbmc.log()</code> only. Python's standard <code>logging</code> module produces zero output in Kodi addon context. All runtime diagnostics use <code>xbmc.log("[m3sr2019] ...", xbmc.LOGWARNING)</code>. Filter the Kodi log on <code>[m3sr2019]</code> to isolate addon output. (<code>%APPDATA%\Kodi\kodi.log</code> on Windows.)</li>
  <li><strong>Song search track IDs:</strong> The site no longer includes an <code>id</code> attribute on <code>&lt;tr class="song"&gt;</code> elements in search results. <code>track_id</code> is reconstructed as <code>"song_" + rel</code>, which is valid because <code>boo()</code> uses <code>track_id[5:]</code> == <code>rel</code>. End-to-end playback from search results should be verified on first use.</li>
  <li><strong>Label strategy:</strong> Aeon Nox Silvo List view renders one label line per item. All album and song ListItems embed the artist in the primary label as <code>"Artist — Title"</code>. <code>setLabel2(artist)</code> is also set for skins that do show a subtitle.</li>
  <li><strong>DB chunking:</strong> Track inserts are chunked at 100 rows to stay clear of SQLite's 999-variable limit on large albums.</li>
</ul>

<hr>

<h2>Changelog</h2>

<h3>v2026.1.0 — Initial Release</h3>

<p>Complete modernisation of the original MP3 Streams Reloaded v0.7 (2022) codebase. All work from the development cycle (v2026.1 through v2026.3.22) is included. Version reset to 2026.1.0 for public release.</p>

<h4>Foundation</h4>
<ul>
  <li>100% Python 3 native; all Python 2/3 bridge modules and deprecated dependencies removed.</li>
  <li>Updated settings and metadata handling for Kodi 19+.</li>
  <li>Fixed multiple crash paths and routing errors from the original codebase.</li>
  <li>Modernised headers, User-Agent, Referer logic, and CDN token generation.</li>
</ul>

<h4>Session &amp; Caching</h4>
<ul>
  <li>Resilient HTML caching with content validation — bad pages (login walls, empty responses) are never written to cache and detected/purged if already present.</li>
  <li>Session warmup before every listing and search request; retry-on-empty with automatic session refresh.</li>
  <li>Cookie persistence after every successful fetch (not just at shutdown).</li>
  <li>HTTP backoff retries on transient network and 5xx errors.</li>
</ul>

<h4>Features</h4>
<ul>
  <li>Song search — fully operational, including <code>track_id</code> reconstruction from <code>rel</code> when the site omits <code>tr id</code>.</li>
  <li>Favourites system — Save/Remove for albums, artists, and songs. Kind-specific labels: <em>My Albums</em>, <em>My Artists</em>, <em>My Songs</em>. Toast notifications on add/remove.</li>
  <li>Play Album / Shuffle Album context menu actions — builds and starts a Kodi playlist without opening the album first.</li>
  <li>Shuffle Favourite Songs — one-click home screen action.</li>
  <li>Toggle Visualizer — correct window-state detection.</li>
  <li>Music Virtualizer toggle — reads/writes <code>audiooutput.stereoupmix</code> via JSON-RPC; state-aware label per directory load.</li>
  <li>Expanded album metadata: genre, year, description surfaced on track ListItems.</li>
  <li>Fanart support during playback (album art fills Now Playing background).</li>
  <li>Unified <code>InfoTagMusic</code> metadata throughout; deprecated <code>setInfo()</code> fully removed.</li>
</ul>

<h4>Correctness &amp; Skin Compatibility</h4>
<ul>
  <li>Artist name embedded in all album and song listing labels (<code>"Artist — Title"</code>) for single-line skin compatibility (Aeon Nox Silvo and others).</li>
  <li><code>setAlbumArtist()</code> set alongside <code>setArtist()</code> so both track-level and album-level artist fields are always populated.</li>
  <li>Genre album listing artist parsing uses ancestor-aware search (<code>_find_album_sibling()</code>) to handle variable HTML nesting depth.</li>
  <li>Large album crash fixed — SQLite 999-variable limit avoided by chunking inserts at 100 rows.</li>
  <li>Artist page listing fixed — required fields that are absent on artist pages are now treated as optional.</li>
</ul>

<hr>

<h2>Open Item</h2>

<p>Song search playback end-to-end has not been formally verified after the <code>track_id</code> reconstruction fix. Select a search result and confirm audio plays. If playback fails with an auth error, verify that <code>boo(track_id)</code> where <code>track_id = "song_" + rel</code> produces the correct CDN token. Album track playback is unaffected and was never broken.</p>
