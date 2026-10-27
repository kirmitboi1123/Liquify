#!/bin/bash
# Re-applies Spicetify after Spotify updates itself (Mac port of the Windows logon task).
#
#   spicetify-reapply.sh login   run by the LaunchAgent at login: waits 60 s first, settles 60 s
#   spicetify-reapply.sh now     "fix it now": no login wait, settles 15 s
#
# Rules (each one cost a broken setup on Windows):
# - Spotify's Apps folder is in one of three states:
#     patched  = no xpui.spa, and xpui/helper/*.js contains "spicetify"
#     clean    = xpui.spa present: Spotify just updated, any extracted folders are stale
#     updating = neither: wait (up to 5 min) for the updater to finish
# - patched -> apply.  clean -> move stale folders and the old Backup aside (never delete),
#   reset [Backup] version, then backup apply; on failure run `spicetify update` once and retry.
# - Never run `spicetify backup` unless a clean xpui.spa exists right now.
# - Before every apply, merge the css-map additions back in (`spicetify update` replaces
#   css-map.json) and apply through a dead proxy so Spicetify uses the local css-map.
#   If the merge changed the map while Spotify is patched, use `restore backup apply`.
# - Spotify can update mid-run: after applying, wait, check again, loop up to 3 times.
# - The log ends in "VERIFIED patched (Spotify x.y.z)" or "ERROR: ...".

MODE="${1:-now}"
SPICETIFY="$HOME/.spicetify/spicetify"
APPS="/Applications/Spotify.app/Contents/Resources/Apps"
PORT_DIR="$HOME/.config/spicetify/mac-port"
CONFIG="$HOME/.config/spicetify/config-xpui.ini"
ADDITIONS="$HOME/.config/spicetify/css-map-additions.json"
CSS_MAP="$HOME/.spicetify/css-map.json"
STATE_DIR="$HOME/.local/state/spicetify"
LOG="$PORT_DIR/reapply.log"
LOCK="$PORT_DIR/.reapply.lock"
DEAD_PROXY="http://127.0.0.1:9"
export PATH="$HOME/.spicetify:/usr/bin:/bin:/usr/sbin:/sbin"

if [ "$MODE" = login ]; then LOGIN_WAIT=60; SETTLE=60; else LOGIN_WAIT=0; SETTLE=15; fi

# Writes to the log and stderr (not stdout, so functions that echo a value can call it).
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

# Strip colour codes, carriage-return spinners and progress bars from Spicetify's output.
clean_output() {
	sed -E $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g' | tr '\r' '\n' \
		| grep -vE '^[[:space:]]*[-\\|/][[:space:]]' | grep -vE 'Patching files|^[[:space:]]*$' \
		| uniq | sed 's/^/    /'
}

# Runs spicetify with the given args; through the dead proxy unless the first arg is "update".
run_spicetify() {
	log "spicetify $*"
	local status
	if [ "$1" = update ]; then
		"$SPICETIFY" "$@" </dev/null 2>&1 | clean_output | tee -a "$LOG"
		status=${PIPESTATUS[0]}
	else
		HTTPS_PROXY="$DEAD_PROXY" https_proxy="$DEAD_PROXY" "$SPICETIFY" "$@" </dev/null 2>&1 | clean_output | tee -a "$LOG"
		status=${PIPESTATUS[0]}
	fi
	return "$status"
}

state() {
	if [ -f "$APPS/xpui.spa" ]; then echo clean
	elif [ -d "$APPS/xpui/helper" ] && grep -qs spicetify "$APPS"/xpui/helper/*.js; then echo patched
	else echo updating
	fi
}

spotify_running() { pgrep -xq Spotify; }

# Applying closes Spotify and, when run from launchd, nothing restarts it. Reopen it hidden
# (Dock icon brings it up) if it was open before the apply.
reopen_spotify() {
	[ "$1" = yes ] || return 0
	sleep 5
	spotify_running && return 0
	log "reopening Spotify (hidden) since it was open before applying"
	open -g -j -a Spotify
}

spotify_version() { defaults read /Applications/Spotify.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null || echo unknown; }

# Waits while Spotify's updater is mid-way (no .spa, no patched folder), up to 5 minutes.
wait_until_settled() {
	local waited=0 s
	s=$(state)
	while [ "$s" = updating ] && [ "$waited" -lt 300 ]; do
		[ "$waited" -eq 0 ] && log "Spotify is updating (neither clean nor patched); waiting up to 5 min"
		sleep 10; waited=$((waited + 10)); s=$(state)
	done
	echo "$s"
}

# Merges the css-map additions; returns 0 if css-map.json changed, 1 if not, 2 on error.
merge_css_map() {
	local out status
	out=$(/usr/bin/python3 -I "$PORT_DIR/merge_cssmap.py" "$ADDITIONS" "$CSS_MAP" 2>&1); status=$?
	log "$out"
	case $status in
		10) return 0 ;;
		0) return 1 ;;
		*) return 2 ;;
	esac
}

# Clean Spotify: move stale extracted folders and the old Backup aside, reset the backup version.
prepare_clean() {
	local stale="$STATE_DIR/Backup-stale/$(date +%Y%m%d-%H%M%S)"
	mkdir -p "$stale"
	for d in "$APPS/xpui" "$APPS/login"; do
		[ -d "$d" ] && mv "$d" "$stale/Apps-$(basename "$d")" && log "moved stale $d -> $stale"
	done
	for d in "$STATE_DIR/Backup" "$STATE_DIR/Extracted"; do
		[ -d "$d" ] && mv "$d" "$stale/$(basename "$d")" && log "moved old $d -> $stale"
	done
	sed -i '' -E '/^\[Backup\]/,/^\[/ s/^version[[:space:]]*=.*/version = /' "$CONFIG"
	log "reset [Backup] version in config-xpui.ini"
}

apply_clean() {
	prepare_clean
	merge_css_map; [ $? -eq 2 ] && { log "ERROR: css-map merge failed"; return 1; }
	[ -f "$APPS/xpui.spa" ] || { log "ERROR: xpui.spa vanished before backup; not running backup"; return 1; }
	run_spicetify backup apply && return 0
	log "backup apply failed; running spicetify update once (no proxy) and retrying"
	run_spicetify update
	merge_css_map; [ $? -eq 2 ] && { log "ERROR: css-map merge failed"; return 1; }
	[ -f "$APPS/xpui.spa" ] || { log "ERROR: no clean xpui.spa for the retry; not running backup"; return 1; }
	run_spicetify backup apply
}

apply_patched() {
	merge_css_map; local changed=$?
	[ $changed -eq 2 ] && { log "ERROR: css-map merge failed"; return 1; }
	if [ $changed -eq 0 ]; then run_spicetify restore backup apply; else run_spicetify apply; fi
}

main() {
	if ! mkdir "$LOCK" 2>/dev/null; then
		echo "Another reapply run is in progress ($LOCK); exiting." | tee -a "$LOG"
		exit 0
	fi
	trap 'rmdir "$LOCK" 2>/dev/null' EXIT

	echo >>"$LOG"
	log "===== Spicetify reapply ($MODE), Spotify $(spotify_version) ====="
	[ -x "$SPICETIFY" ] || { log "ERROR: $SPICETIFY not found"; exit 1; }
	[ "$LOGIN_WAIT" -gt 0 ] && { log "login: waiting ${LOGIN_WAIT}s for Spotify's updater"; sleep "$LOGIN_WAIT"; }

	local attempt s was_running
	for attempt in 1 2 3; do
		s=$(wait_until_settled)
		log "attempt $attempt: state = $s"
		was_running=no; spotify_running && was_running=yes
		case $s in
			patched) apply_patched || { log "ERROR: apply failed (state was patched)"; exit 1; } ;;
			clean) apply_clean || { log "ERROR: re-patching a freshly updated Spotify failed"; exit 1; } ;;
			*) log "ERROR: Spotify still updating after 5 min (no xpui.spa, no patched xpui/)"; exit 1 ;;
		esac
		reopen_spotify "$was_running"
		log "applied; waiting ${SETTLE}s in case Spotify updates mid-run"
		sleep "$SETTLE"
		s=$(state)
		if [ "$s" = patched ]; then
			log "VERIFIED patched (Spotify $(spotify_version))"
			exit 0
		fi
		log "state is '$s' after applying; Spotify changed underneath us, looping"
	done
	log "ERROR: still not patched after 3 attempts (state = $(state))"
	exit 1
}

main
