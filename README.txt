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
python3 -m pip install --break-system-packages -r requirements.txt
streamlit run app.py

Headless startup check:
python3 -m pytest -q tests/test_app_startup_smoke.py

Manual startup check on a free port:
PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)
timeout 20s streamlit run app.py --server.headless true --server.port "$PORT"

Validation:
python3 -m pytest -q
python3 -m compileall app.py grade_engine tests
