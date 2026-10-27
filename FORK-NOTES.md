# Liquify — local fork for Spotify 1.3.5.3058 (2026-10-16)

Upstream: https://github.com/NMWplays/Liquify (main @ 419612d, "Fixes for Spotify V 1.3.3").
Branch here: `spotify-1.3.5`, pushed to https://github.com/kirmitboi1123/Liquify (remote `fork`).

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

Rebuild after editing (the 4th argument is the css-map Spicetify actually applies; see the 1.3.6
section for why it matters):
`python tools/patch_theme.py tools/classmap-final.json . build "%LOCALAPPDATA%\spicetify\css-map.json"`,
copy `build\*` to the theme folder, `spicetify refresh`.

## Verified (screenshots over CDP, 1080x824 window)

Home, Liked Songs, Search, playlist, album and artist pages, now-playing sidebar: glass
panels, floating glass player, up-next card bottom-left (x=8, y=636, above the player).
Playlist/album/artist fixes added 2026-10-17 (compat CSS). Not checked: fullscreen/cinema,
lyrics view, settings panel, context menus, podcast/episode pages.

## When it will break / how to undo

- **Next Spotify update** may regenerate the hashes again (1.3.6 did not, see below). The css-map
  additions survive now: they live in `%APPDATA%\spicetify\css-map-additions.json`, and the logon
  script (`Documents\automated\spicetify-reinstall.ps1`) merges them back into css-map.json and
  applies with the dead-proxy trick on every run.
- **When upstream Liquify or Spicetify ships a 1.3.5 fix**, switch back to the Marketplace copy:
  `spicetify config current_theme marketplace` then `spicetify restore backup apply`.

## Spotify 1.3.6.1921 + Spicetify 2.46.3 (2026-10-25)

- **1.3.6 kept the 1.3.5 hashes.** 6663 of 6692 CSS classes are unchanged, and all 225 hashed
  classes this theme uses are still there. The theme broke only because Spotify updated *during*
  the logon script (patch dropped, stale 1.3.5 `Apps\xpui\` left next to a clean `xpui.spa`).
- **Spicetify 2.46.3's css-map renames 30 classes this theme targeted by raw hash** (top bar,
  entity header, home shortcuts, right-sidebar peek/overlay). Spicetify renames those classes in
  Spotify too, so the raw-hash selectors matched nothing. `patch_theme.py` now takes the applied
  css-map as a 4th argument and rewrites them (46 in user.css, 22 in theme.js).
- **1.3.6 rebuilt the now-playing view (right sidebar) with new classes.** None of the theme's 1.3.5
  NPV hashes are in its DOM any more (they survive elsewhere in the CSS bundle, which is why the
  "all 225 hashes still exist" check passed). Mapped in `compat-1.3.5.css`: container
  `vVF0gCDG9l8RCOK3_2kw` (was painting #121212; also sets `--section-background-base`, the #242424
  of the Credits / Next in queue cards), header `_qEwikUlZSIdhG1eHl6y` (was `tlJt8JO80alw0Nlw6iW9`;
  scroll-driven animation painted it #121212), top spacing `HuKs8FZg6Y75cV9Lh0Kk` (was
  `AfKmrZ306qeQTbYQfwLc`). Lesson: "hash still exists in the CSS" is not "hash still in the DOM";
  probe the live DOM for painted backgrounds.
- Remote css-map (main == 2.46.3) covers only 21 of the 336 additions, so the additions are
  still required.
- Verified over CDP: home, Liked Songs, album page, now-playing sidebar all glass; up-next card
  bottom-left. Not checked: lyrics, fullscreen, settings, podcasts.
