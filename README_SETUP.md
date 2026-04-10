# CNC Tool Engine Setup

## Install

From the repo root:

Windows PowerShell:

```powershell
py -m pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m pip install -r requirements.txt
```

## Run the app

Windows PowerShell:

```powershell
py -m streamlit run app.py
```

Linux / macOS:

```bash
python3 -m streamlit run app.py
```

For an automated headless launch check with a free port:

Windows PowerShell:

```powershell
py -m pytest -q tests/test_app_startup_smoke.py
```

Linux / macOS:

```bash
python3 -m pytest -q tests/test_app_startup_smoke.py
```

For a manual headless launch check on a known free port:

Windows PowerShell:

```powershell
$port = py -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()"
py -m streamlit run app.py --server.headless true --server.port $port --browser.gatherUsageStats false
```

Linux / macOS:

```bash
PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)
python3 -m streamlit run app.py --server.headless true --server.port "$PORT" --browser.gatherUsageStats false
```

If Streamlit starts and prints the local URL, startup is clean. Stop it with `Ctrl+C` after the URL appears.

## Run tests

Windows PowerShell:

```powershell
py -m pytest -q
```

Linux / macOS:

```bash
python3 -m pytest -q
```

## Validate bytecode compilation

Windows PowerShell:

```powershell
py -m compileall app.py grade_engine tests
```

Linux / macOS:

```bash
python3 -m compileall app.py grade_engine tests
```

## What is covered

- Turning inserts
- Grooving inserts
- Threading inserts
- Drills
- Endmills
- Face mills
- Taps
- Reamers

Every tool family now returns a live recommendation, supplier search links, and shop-facing setup guidance from the same input panel. Non-turning supplier searches are built from tool style, geometry, hole style, and material terms instead of turning-insert coating jargon.
