#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILE="$REPO_ROOT/codex_prompts/cnc_tool_engine_master_prompt.txt"
LOG_DIR="$REPO_ROOT/.codex-agent/logs"
STATE_DIR="$REPO_ROOT/.codex-agent/state"

mkdir -p "$LOG_DIR" "$STATE_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/codex_multi_pass_${TIMESTAMP}.log"
MAX_PASSES=3
PASS=1

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Missing prompt file: $PROMPT_FILE" >&2
  exit 1
fi

cd "$REPO_ROOT"

while [[ "$PASS" -le "$MAX_PASSES" ]]; do
  echo "[$(date)] Codex pass $PASS of $MAX_PASSES" | tee -a "$LOG_FILE"
  cat "$PROMPT_FILE" | codex --yolo 2>&1 | tee -a "$LOG_FILE" || true

  if [[ -z "$(git status --porcelain)" ]]; then
    echo "[$(date)] No further repo changes detected after pass $PASS." | tee -a "$LOG_FILE"
    break
  fi

  PASS=$((PASS + 1))
done

echo "$TIMESTAMP" > "$STATE_DIR/last_run.txt"
echo "0" > "$STATE_DIR/last_exit_code.txt"
