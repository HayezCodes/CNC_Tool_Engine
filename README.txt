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
timeout 20s streamlit run app.py --server.headless true --server.port 8513

If port 8513 is already taken on your machine, rerun the same command with any other open port.

Validation:
python3 -m pytest -q
python3 -m compileall app.py grade_engine tests
