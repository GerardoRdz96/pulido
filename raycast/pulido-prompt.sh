#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Pulido: Prompt
# @raycast.mode silent
# Optional parameters:
# @raycast.icon 🪄
# @raycast.packageName Pulido
# Documentation:
# @raycast.description Shape clipboard dictation into a clear coding-agent prompt → clipboard
PATH="$HOME/.local/bin:$HOME/.local/pipx/venvs/pulido/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
pulido --mode prompt
