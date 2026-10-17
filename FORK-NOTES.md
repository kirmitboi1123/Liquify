# Liquify — local fork for Spotify 1.3.5.3058 (2026-10-16)

Upstream: https://github.com/NMWplays/Liquify (main @ 419612d, "Fixes for Spotify V 1.3.3").
Branch here: `spotify-1.3.5`. Not pushed anywhere.

## Why it broke

Spotify auto-updated 1.3.4 -> 1.3.5.3058 on 2026-10-16. Every hashed CSS class was
regenerated, and Spicetify 2.45.3's css-map (and even its unreleased main-branch map)
covers almost none of this build, so the readable names Liquify relies on
(`Root__now-playing-bar`, `Root__main-view`, ...) stopped existing. Result: black panels,
default player, the up-next card stuck top-left. Same reports upstream: issues #22-#24.

## What was done (two layers)

1. **Spicetify css-map, extended.** `tools/css-map-additions-1.3.5.3058.json` (336 entries,
   new 1.3.5 hash -> readable name), found by diffing Spotify 1.3.4's Spicetify-patched CSS
   (`%APPDATA%\spicetify\Backup-stale\xpui-20261016-215217`) against clean 1.3.5.
   Merged into `%LOCALAPPDATA%\spicetify\css-map.json` (release map backed up next to it as
   `css-map.2.45.3-release.json.bak`). Readable names in the live app went 24 -> 137.
   - Spicetify ignores the local map unless the remote fetch fails, so the rebuild was run as:
     `HTTPS_PROXY=http://127.0.0.1:9 spicetify restore backup apply`
2. **Theme patch.** `tools/patch_theme.py` rewrites Liquify's 1.3.3-era hashes using
   `tools/classmap-final.json` (CSS diff + Liquify's own git history + `tools/manual-map.json`),
   and appends `tools/compat-1.3.5.css` for the few gaps found by eye. Output: `build/`.
   Installed as the local theme `%APPDATA%\spicetify\Themes\Liquify-1.3.5`.

Rebuild after editing: `python tools/patch_theme.py tools/classmap-final.json . build`, copy
`build\*` to the theme folder, `spicetify refresh`.

## Verified (screenshots over CDP, 1080x824 window)

Home, Liked Songs, Search, playlist, album and artist pages, now-playing sidebar: glass
panels, floating glass player, up-next card bottom-left (x=8, y=636, above the player).
Playlist/album/artist fixes added 2026-10-17 (compat CSS). Not checked: fullscreen/cinema,
lyrics view, settings panel, context menus, podcast/episode pages.

## When it will break / how to undo

- **Next Spotify update** (1.3.6 is already rolling out) regenerates the hashes again. The logon
  script's `backup apply` will fetch Spicetify's remote map and drop the additions. Expect the
  same symptoms.
- **When upstream Liquify or Spicetify ships a 1.3.5 fix**, switch back to the Marketplace copy:
  `spicetify config current_theme marketplace` then `spicetify restore backup apply`.
