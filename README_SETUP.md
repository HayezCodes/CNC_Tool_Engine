# CNC Tool Engine Setup

## Install

From the repo root:

```bash
python3 -m pip install --break-system-packages -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

For an automated headless launch check with a free port:

```bash
python3 -m pytest -q tests/test_app_startup_smoke.py
```

For a manual headless launch check on a known free port:

```bash
PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)
timeout 20s streamlit run app.py --server.headless true --server.port "$PORT"
```

If Streamlit starts and prints the local URL before the timeout stops it, startup is clean.

## Run tests

```bash
python3 -m pytest -q
```

## Validate bytecode compilation

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
