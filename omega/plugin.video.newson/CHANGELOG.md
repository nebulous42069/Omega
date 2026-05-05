# NewsON Addon v2.0.0 - Changelog

## Major Changes (v2.0.0)

### API Migration
- **Migrated from old API to NewsON v5 API**
  - Old: `https://newson.us/api/`
  - New: `https://newson-api.triple-it.nl/v5api/`
- Updated all API endpoints to work with the new v5 structure
- Fixed geolocation handling using new config endpoint
- Removed deprecated MapQuest integration

### HTTP Client Replacement
- **Replaced `requests` module with custom `client.py`**
  - Faster and more reliable HTTP client
  - Built-in Cloudflare and DDoS-Guard protection
  - Session management and cookie persistence
  - Better SSL/TLS handling
  - Reduced dependencies

### Code Improvements
- Removed `script.module.requests` dependency
- Removed `gzip` and `base64` imports (handled by client)
- Cleaner code structure with better error handling
- Improved caching mechanism
- Better video stream URL resolution

### Bug Fixes
- Fixed broken API endpoints
- Removed hardcoded MapQuest API key
- Fixed station browsing by state/city
- Improved live vs VOD content handling
- Better error messages for failed requests

### New Features
- Support for new VOD content types
- Better station metadata (logos, covers, etc.)
- Improved live content detection with [LIVE] tags
- Support for breaking news endpoint
- Enhanced video playback with proper stream URL resolution

## Files Modified

1. **resources/lib/newson.py** - Complete rewrite
   - New API integration
   - Client module integration
   - Improved data parsing
   - Better video item building

2. **addon.xml** - Updated
   - Version bumped to 2.0.0
   - Removed deprecated status
   - Removed requests dependency
   - Updated website URL

3. **resources/settings.xml** - Simplified
   - Removed MapQuest API key setting
   - Kept debug mode toggle

4. **resources/lib/client.py** - Already present
   - Custom HTTP client with advanced features

5. **resources/lib/ui/control.py** - Created
   - Support module for client.py
   - Settings and path management

## Testing Recommendations

1. **Main Menu**
   - Open addon and verify main menu shows 4 options
   - Live Now, Breaking News, Local, Browse by States

2. **Live Content**
   - Test "Live Now" section shows current broadcasts
   - Verify [LIVE] tags appear on live content

3. **Station Browsing**
   - Browse states → cities → stations
   - Verify station logos and metadata load correctly

4. **Video Playback**
   - Test playing live streams
   - Test playing VOD content
   - Verify HLS streams play correctly

5. **Error Handling**
   - Test with no internet connection
   - Verify error notifications appear

## Known Limitations

1. Breaking news endpoint may return empty results (depends on NewsON's feed)
2. Some VOD content may not have playback URLs immediately available
3. Geolocation is determined by NewsON's API (not user-configurable)

## Future Improvements

- Add favorites support
- Implement search functionality
- Add manual location override
- Support for additional content types (sports, weather)
- Implement better caching strategies
