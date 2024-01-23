## PVR artwork module ##

This module is a helper module for scraping PVR related content from Kodi database, file system or from TMDB and fanart.tv. Generated 
content is cached for 90, 180 or 360 days. The search process is as follows:

- Previously cached content is read out. The title, year of release and media type (film/series) of a series or film serve as criteria.
- the series/movies available in the databases are checked for hits with the title to be searched and the information (artwork, meta data) is provided.
- previously defined folders are checked for hits with the titles to be searched and the artwork available in these folders is provided. This process cannot provide textual metadata (genre, release date, etc.).
- the final step involves searching for a series/movie on TMDB.org. This requires a valid API key in addition to an online connection. Artwork available at TMDB as well as metadata will be provided. Additional fanart from fanart.tv (API key required) will read out if TMDB search contains an imdb or tvdb id. 

The functions of the module is called periodically from an integrated service (main.py) when the following PVR windows are displayed

- MyPVRChannels.xml
- MyPVRGuide.xml
- MyPVRRecordings.xml
- MyPVRTimers.xml
- MyPVRSearch.xml

or videoplayer (Video OSD) is present.

All labels and artwork will be set as Properties in Home window, e.g. `Window(10000).Property('PVR.Artwork.ListItem.director')` or `Window(10000).Property('PVR.Artwork.clearart')`

Unless information provided by ListItems changes, metadata and artwork do not need to be updated. If none of the above windows are displayed, all Properties of PVR Artwork Module in Home window will be cleared.

### Labels ###

`PVR.Artwork.ListItem.director`, `PVR.Artwork.ListItem.writer`, `PVR.Artwork.ListItem.genre`, `PVR.Artwork.ListItem.country`, `PVR.Artwork.ListItem.studio`, `PVR.Artwork.ListItem.studiologo`, `PVR.Artwork.ListItem.premiered`, `PVR.Artwork.ListItem.mpaa`, `PVR.Artwork.ListItem.status`, `PVR.Artwork.ListItem.rating`,`PVR.Artwork.ListItem.ratings`, `PVR.Artwork.ListItem.ratings.imdb`, `PVR.Artwork.ListItem.ratings.tmdb`, `PVR.Artwork.ListItem.ratings.themoviedb`, `PVR.Artwork.ListItem.castandrole`, `PVR.Artwork.ListItem.description`, `PVR.Artwork.ListItem.is_db`

Note that PVR.Artwork.ListItem.is_db contains the full path of "media/defaultnas.png".

### Artwork ###

Artwork depends on the presence of artwork files in file system (cache), database or online (TMDB):

`PVR.Artwork.fanart`, `PVR.Artwork.poster`, `PVR.Artwork.poster1` ... `PVR.Artwork.poster5`, `PVR.Artwork.fanart1` ... `PVR.Artwork.fanart5`

additional Artwork: 

`PVR.Artwork.thumb` (folder.jpg), `PVR.Artwork.discart` (discart.jpg), `PVR.Artwork.banner` (banner.jpg), `PVR.Artwork.logo` (logo.png), `PVR.Artwork.clearlogo` (clearlogo.png), `PVR.Artwork.clearart` (clearart.png), `PVR.Artwork.characterart` (characterart.png), `PVR.Artwork.landscape` (landscape.jpg)

### Others ###

The PVR Artwork Module has a label `PVR.Artwork.Lookup`. If this label contains the value `busy` the module is processing a PVR item at this moment. This can be used to show a "Busy"-Spinner or something else to signaling a work in progress.