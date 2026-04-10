#!/usr/bin/env bash
SESSION_NAME="codex_cnc_agent"
tmux new-session -d -s "$SESSION_NAME" "bash scripts/watch_codex_loop.sh"
echo "Started session: $SESSION_NAME"
