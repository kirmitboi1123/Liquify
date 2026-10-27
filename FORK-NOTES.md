# Liquify — local fork for Spotify 1.3.5.3058 (2026-10-16)

Upstream: https://github.com/NMWplays/Liquify (main @ 419612d, "Fixes for Spotify V 1.3.3").
Branch here: `spotify-1.3.5`, pushed to https://github.com/kirmitboi1123/Liquify (remote `fork`).
macOS build: branch `spotify-1.3.6-mac`, folder `build-mac/` (see "macOS" at the end).

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
   - `tools/merge-cssmap.ps1` does the merge without Python (missing keys only, Spicetify wins on
     a conflict, no BOM, original kept as `css-map.<sha>.json.bak`); it ships in the Windows release
     zip. On a stock 2.46.3/2.46.4 map it adds 315 entries, identical to the map in use here.
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

## macOS: Spotify 1.3.6.1921 (2026-10-26, built and verified on the Mac)

**`build/` matches nothing on macOS.** The Mac build of the same Spotify release
(1.3.6.1921.g7086c071a617) uses completely different CSS class hashes: 0 of the theme's hashed
classes and 0 of the 336 css-map additions exist in the Mac's `xpui.spa`. Spicetify's own
`css-map.json` holds Windows and macOS keys side by side, but ~100 of its Windows-only entries have
no macOS twin.

**Windows-to-Mac class map.** Same release, so both builds have the same CSS rules in the same
order, only renamed. `tools/winmac_map.py` replaces every class name with a placeholder, aligns CSS
files whose skeletons are identical class by class (53 of 96 files exactly; chunk ids differ, so
leftover files pair by identical skeleton), aligns near-identical files rule by rule with difflib,
and counts every pairing as a vote: 6,562 classes, 0 conflicting votes, 0 many-to-one. Three
classes in `xpui-snapshot.css` were matched by hand on identical rule bodies (one candidate each):
`MhNxqEtcoJ7NTbdrVaZz` -> `p63irlHLPRPNuhXrkoKr`, `zUXTETXFM98g23SLSxFj` -> `yppiCd4J5oZzmncksrhi`,
`fL8UiTknkJJAXqnUv932` -> `TxO4cJyIggVYNxMM2az4`. Result: `tools/win2mac-1.3.6.1921.json` (6,565
entries, 5,356 renamed). Coverage, rechecked on Windows against both clean `xpui.spa` files: user.css
187/187 hashes mapped and present on the Mac, theme.js 40/40, css-map additions 336/336.

**Mac css-map additions.** `tools/css-map-additions-mac-1.3.6.1921.json` (434 entries) = the 336
Windows additions with keys translated (readable names unchanged) + 98 macOS twins of Spicetify's
own Windows-only entries (needed because `patch_theme.py`'s 4th argument rewrote the theme to those
readable names). Merge with `tools/merge_cssmap.py` (missing keys only, Spicetify wins on conflict,
UTF-8 without BOM, original saved as `css-map.<sha>.json.bak`). **The theme only works with these
merged and applied through the dead proxy**, exactly like the Windows additions.

**`build-mac/`** = `build/` translated through the map (user.css 272 replacements, theme.js 43), then
the css-map renames (1 in user.css: `eO_TtjpETEJ3VwmJEn0S` -> `main-card-card`). Rebuild for a new
Spotify version (extract both clean `xpui.spa` files first; they are zips):

```
python3 tools/winmac_map.py <win_xpui_dir> <mac_xpui_dir> tools/win2mac-<ver>.json   # then add the 3 hand-matched entries
python3 tools/make_mac_port.py tools/win2mac-<ver>.json . <Spicetify's unmerged css-map.json> /tmp/macport
cp /tmp/macport/css-map-additions.json tools/css-map-additions-mac-<ver>.json
python3 tools/merge_cssmap.py tools/css-map-additions-mac-<ver>.json ~/.spicetify/css-map.json
cp tools/patch_theme.py /tmp/macport/   # run a copy: next to compat-1.3.5.css it appends it again, and build/ already has it
python3 /tmp/macport/patch_theme.py /tmp/macport/mac-map.json build build-mac ~/.spicetify/css-map.json
```

`patch_theme.py` now writes with `write_bytes`: `write_text(newline=...)` needs Python 3.10 and macOS
ships 3.9.6 as `/usr/bin/python3`.

**Mac paths.** css-map `~/.spicetify/css-map.json`; config and themes `~/.config/spicetify/`;
Spicetify backup `~/.local/state/spicetify/Backup/` (not `~/.config`).

**Auto re-apply (`mac/`), the Windows logon task ported.** `spicetify-reapply.sh` keeps every Windows
rule: three states (patched / clean / updating, wait up to 5 min); clean -> move stale `Apps/xpui`,
`Apps/login`, Backup and Extracted to `~/.local/state/spicetify/Backup-stale/<time>/` and reset
`[Backup] version`; never `backup` without a clean `xpui.spa`; merge css-map + dead proxy before every
apply (`restore backup apply` if the merge changed the map while patched); `spicetify update` once on
failure; settle, recheck, loop up to 3 times; log ends in `VERIFIED patched (Spotify x.y.z)`; a lock
stops overlapping runs. Mac-only: from launchd, `spicetify apply` closes Spotify and nothing restarts
it, so the script reopens Spotify if it was open. The LaunchAgent is RunAtLoad only (WatchPaths would
retrigger itself through "patched -> apply"). Assumes Spicetify at `~/.spicetify/spicetify`. Install:

```
mkdir -p ~/.config/spicetify/mac-port
cp mac/spicetify-reapply.sh "mac/Fix Spicetify.command" tools/merge_cssmap.py ~/.config/spicetify/mac-port/
chmod +x ~/.config/spicetify/mac-port/spicetify-reapply.sh ~/.config/spicetify/mac-port/"Fix Spicetify.command"
cp tools/css-map-additions-mac-1.3.6.1921.json ~/.config/spicetify/css-map-additions.json
sed "s|__HOME__|$HOME|g" mac/app.spicetify.reapply.plist > ~/Library/LaunchAgents/app.spicetify.reapply.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/app.spicetify.reapply.plist
```

Double-click `~/.config/spicetify/mac-port/Fix Spicetify.command` to re-apply now (no login wait).
Log: `~/.config/spicetify/mac-port/reapply.log`.

**Verified on the Mac (macOS 15.6.1, Apple Silicon, Spicetify 2.46.4), CDP screenshots + live DOM:**
home, Liked Songs, album page, now-playing sidebar: glass panels, 0 large opaque dark elements,
floating glass player, up-next card bottom-left above the player; readable `Root__`/`main-` names in
the DOM 138 (Windows 137). The Quick Queue fix (spicetify-extensions branch `quickqueue-spotify-1.3.6`)
works unchanged. Re-apply script tested: closed Spotify, reopened it ~8 s later, `VERIFIED patched`.
Not checked: lyrics view, fullscreen/cinema, settings, podcasts.
