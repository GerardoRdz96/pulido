#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Pulido: Clean
# @raycast.mode silent
# Optional parameters:
# @raycast.icon 🪄
# @raycast.packageName Pulido
# Documentation:
# @raycast.description Polish clipboard dictation, keep the language mix → clipboard
PATH="$HOME/.local/bin:$HOME/.local/pipx/venvs/pulido/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
pulido --mode clean
