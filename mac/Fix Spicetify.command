#!/bin/bash
# Double-click to re-apply Spicetify now (no login wait). Same script the login agent runs.
"$HOME/.config/spicetify/mac-port/spicetify-reapply.sh" now
echo
echo "Log: $HOME/.config/spicetify/mac-port/reapply.log"
read -r -p "Press Return to close."
