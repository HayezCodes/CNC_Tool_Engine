#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILE="$REPO_ROOT/codex_prompts/cnc_tool_engine_master_prompt.txt"
LOG_DIR="$REPO_ROOT/.codex-agent/logs"
STATE_DIR="$REPO_ROOT/.codex-agent/state"

mkdir -p "$LOG_DIR" "$STATE_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/codex_run_${TIMESTAMP}.log"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Missing prompt file: $PROMPT_FILE" >&2
  exit 1
fi

cd "$REPO_ROOT"

echo "[$(date)] Starting Codex exec run..." | tee -a "$LOG_FILE"

codex exec --yolo "$(cat "$PROMPT_FILE")" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "$TIMESTAMP" > "$STATE_DIR/last_run.txt"
echo "$EXIT_CODE" > "$STATE_DIR/last_exit_code.txt"

if [[ "$EXIT_CODE" -eq 0 ]]; then
  echo "[$(date)] Codex run finished successfully." | tee -a "$LOG_FILE"
else
  echo "[$(date)] Codex run failed with exit code $EXIT_CODE." | tee -a "$LOG_FILE"
fi

exit "$EXIT_CODE"