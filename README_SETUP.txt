CNC Tool Engine Setup

Install:
python3 -m pip install --break-system-packages -r requirements.txt

Run:
streamlit run app.py

Headless startup check:
python3 -m pytest -q tests/test_app_startup_smoke.py

Manual startup check:
PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)
timeout 20s streamlit run app.py --server.headless true --server.port "$PORT"

Test:
python3 -m pytest -q

Compile check:
python3 -m compileall app.py grade_engine tests
