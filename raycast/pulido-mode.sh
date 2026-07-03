#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Pulido: Mode…
# @raycast.mode silent
# @raycast.argument1 { "type": "dropdown", "placeholder": "mode", "data": [{"title": "Teams (Spanish)", "value": "teams-es"}, {"title": "Teams (English)", "value": "teams-en"}, {"title": "Social post draft", "value": "linkedin"}, {"title": "Markdown notes", "value": "notes"}] }
# Optional parameters:
# @raycast.icon 🪄
# @raycast.packageName Pulido
# Documentation:
# @raycast.description Polish clipboard dictation into the chosen shape → clipboard
PATH="$HOME/.local/bin:$HOME/.local/pipx/venvs/pulido/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
pulido --mode "$1"
