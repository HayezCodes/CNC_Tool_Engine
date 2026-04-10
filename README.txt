CNC Tool Engine

This Streamlit app gives shop-floor starter recommendations for:
- Turning inserts
- Grooving inserts
- Threading inserts
- Drills
- Endmills
- Face mills
- Taps
- Reamers

Quick start:
Windows PowerShell:
py -m pip install -r requirements.txt
py -m streamlit run app.py

Linux / macOS:
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py

Headless startup check:
Windows PowerShell:
py -m pytest -q tests/test_app_startup_smoke.py

Linux / macOS:
python3 -m pytest -q tests/test_app_startup_smoke.py

Manual startup check on a free port:
Windows PowerShell:
$port = py -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()"
py -m streamlit run app.py --server.headless true --server.port $port --browser.gatherUsageStats false

Linux / macOS:
PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)
python3 -m streamlit run app.py --server.headless true --server.port "$PORT" --browser.gatherUsageStats false

Validation:
Windows PowerShell:
py -m pytest -q
py -m compileall app.py grade_engine tests

Linux / macOS:
python3 -m pytest -q
python3 -m compileall app.py grade_engine tests
