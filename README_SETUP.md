# CNC Codex Background Agent Pack

This pack keeps your prompt text the same and your saved prompt file unchanged.

## Included files

- `codex_prompts/cnc_tool_engine_master_prompt.txt`
- `scripts/run_codex_once.sh`
- `scripts/watch_codex_loop.sh`
- `scripts/start_codex_agent_tmux.sh`
- `scripts/run_codex_once_optional_multi_pass.sh`
- `.codex-agent/logs/`
- `.codex-agent/state/`
- `.codex-agent/queue/`

## Important

Do not edit the prompt file if you want to keep the exact wording the same.

## Windows + WSL setup

### 1) Install WSL
Run in Windows PowerShell as admin:

```powershell
wsl --install
```

Reboot if prompted.

### 2) Open Ubuntu / WSL
Install the small tools needed:

```bash
sudo apt update
sudo apt install -y tmux inotify-tools
```

### 3) Install Node and Codex if needed
If Node is not already installed inside WSL:

```bash
sudo apt install -y nodejs npm
npm install -g @openai/codex
```

### 4) Move this pack into your repo
From WSL, copy these folders into your `CNC_Tool_Engine` repo root so the structure is:

```text
CNC_Tool_Engine/
├─ codex_prompts/
├─ scripts/
└─ .codex-agent/
```

### 5) Make scripts executable

```bash
cd /path/to/CNC_Tool_Engine
chmod +x scripts/*.sh
```

### 6) Start the background runner

```bash
./scripts/start_codex_agent_tmux.sh
```

### 7) Attach to watch it live

```bash
tmux attach -t codex_cnc_agent
```

### 8) Stop it later

```bash
tmux kill-session -t codex_cnc_agent
```

## Optional aggressive option

If you want the optional multi-pass version, run this instead of the single-pass runner manually:

```bash
./scripts/run_codex_once_optional_multi_pass.sh
```

That gives up to 3 stabilization passes in one shot while keeping the same saved prompt text.

## Notes

- The watcher triggers on repo changes.
- The prompt file is fed to Codex as-is.
- Logs go into `.codex-agent/logs/`.
- State files go into `.codex-agent/state/`.
