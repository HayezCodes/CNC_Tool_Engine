# CNC Codex Background Agent Setup

1. Install WSL + Ubuntu
2. Install dependencies:
   sudo apt update
   sudo apt install -y tmux inotify-tools
   npm install -g @openai/codex

3. Make scripts executable:
   chmod +x scripts/*.sh

4. Run:
   ./scripts/start_codex_agent_tmux.sh

5. Attach:
   tmux attach -t codex_cnc_agent
