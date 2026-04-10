CNC Tool Engine Setup

Install:
python3 -m pip install --break-system-packages -r requirements.txt

Run:
streamlit run app.py

Headless startup check:
timeout 20s streamlit run app.py --server.headless true --server.port 8513

Test:
python3 -m pytest -q

Compile check:
python3 -m compileall app.py grade_engine tests
