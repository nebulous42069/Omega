# Kodi Favourites Sync

Kodi service add-on that syncs `favourites.xml` across devices using Google Drive and an OAuth browser pairing flow.

This add-on is designed to stay simple in Kodi:
- Pair once with Google Drive
- Sync automatically on Kodi startup
- Store the remote backup in hidden Google Drive app data

## User Setup

1. Install the add-on.
2. Open add-on settings.
3. Select `Pair Google Drive now`.
4. Complete the sign-in flow in your browser or on your phone.
5. Leave `Sync on Kodi startup` enabled.

After pairing, the add-on will sync `favourites.xml` each time Kodi starts.

## How It Works

- The add-on syncs on Kodi startup only.
- Remote storage uses Google Drive app data by default.
- The backup is not intended to be visible in the normal Drive file list.
- Sync behavior is last-write-wins.

This means the newest `favourites.xml` seen during sync becomes the remote version.

If a device downloads a newer favourites file during startup, Kodi may not always reflect the change in the UI until favourites are reopened or Kodi is restarted again.

## Settings

Visible settings are intentionally minimal:
- `Pair Google Drive now`
- `Sync on Kodi startup`

The add-on also keeps internal OAuth and storage settings for compatibility, but normal users do not need to manage them directly.

## OAuth Bridge

Browser sign-in is handled through the Vercel auth bridge.

Current bridge URL:
- `https://auth-bridge-rho.vercel.app`

## Security Model

The add-on does not contain a Google client secret.

Google sign-in happens in a browser through a separate auth bridge. Kodi shows a pairing code, the user completes Google sign-in in the browser, and the bridge returns tokens to the device through a short-lived pairing record.

The bridge keeps the OAuth client secret on the server side only. Kodi never receives that client secret.

The security goals of this design are:

- no Google client secret inside Kodi
- no manual token copy-paste flow
- one-time token handoff from the bridge to Kodi
- short-lived pairing sessions with explicit expiry
- no public token refresh endpoint

The add-on stores OAuth tokens in Kodi settings after pairing:

- `oauth_refresh_token`
- `oauth_refresh_secret`
- `oauth_access_token`
- `oauth_scope`
- token expiry metadata

The refresh token is used so Kodi can continue syncing on later startups without asking the user to sign in every time.

The additional `oauth_refresh_secret` is required by the bridge before it will exchange a stored refresh token for a new access token. This prevents the bridge from acting as a public refresh endpoint if a refresh token is exposed.

The pairing design is split between a public code and a private device secret:

- Kodi requests a pairing from the bridge
- the bridge returns a user-facing `user_code`
- the bridge also returns a secret `poll_token` known only to Kodi
- the browser authenticates using the `user_code`
- Kodi authenticates polling and claim requests using the `poll_token`

That means the visible browser code alone is not enough to retrieve tokens.

The OAuth flow itself is also kept server-side:

- Google OAuth uses the authorization code flow
- the bridge uses `state` and PKCE
- the Google authorization code is exchanged on the bridge, not in Kodi
- the Google client secret stays only in server-side environment variables

Temporary token handling on the bridge is intentionally narrow:

- token payloads are encrypted before temporary storage
- pairing records are short-lived
- token-bearing responses are marked `no-store`
- the bridge is meant to avoid logging token-bearing payloads
- once Kodi claims a pairing successfully, the bridge deletes the pairing record
- the temporary encrypted token payload and claim keys used for that pairing are deleted immediately after a successful claim

Operationally, the secure deployment assumptions are:

- HTTPS only
- exact Google redirect URIs
- secrets stored only in server-side environment variables
- no production use of an in-memory pairing fallback

## Pairing Flow

1. In Kodi, run `Pair Google Drive now`.
2. The add-on asks the bridge for a pairing session.
3. Kodi shows a code and activation URL.
4. The user signs into Google in a browser.
5. Google redirects back to the bridge.
6. The bridge marks the pairing as authorized.
7. Kodi claims the token payload and stores it locally.

After that, later startup syncs use the saved OAuth state and only contact the bridge when an access token needs to be refreshed.

## Data Access

The add-on requests these Google scopes:

- `openid`
- `email`
- `drive.appdata`
- `drive.file`

`drive.appdata` is the main storage mode. It keeps the sync file in the app's hidden Drive app-data area.

`drive.file` remains available for compatibility with Drive file operations and limited file-based access when needed.
