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

For a headless launch check:

```bash
timeout 20s streamlit run app.py --server.headless true --server.port 8501
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

Every tool family now returns a live recommendation, supplier search links, and shop-facing setup guidance from the same input panel.
