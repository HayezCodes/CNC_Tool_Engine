# CNC Tool Engine

Streamlit app for shop-floor starter recommendations across turning inserts, grooving inserts, threading inserts, drills, endmills, face mills, taps, and reamers.

The app now rebuilds recommendations live as inputs change. Threading adds thread profile and internal or external controls. Tap and reamer flows add hole-type control so the setup guidance and supplier search stay process-specific.

## Install

Windows PowerShell:

```powershell
py -m pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m pip install -r requirements.txt
```

## Run

Windows PowerShell:

```powershell
py -m streamlit run app.py
```

Linux / macOS:

```bash
python3 -m streamlit run app.py
```

## Test

Windows PowerShell:

```powershell
py -m pytest -q
py -m pytest -q tests/test_app_startup_smoke.py
py -m compileall app.py grade_engine tests
```

Linux / macOS:

```bash
python3 -m pytest -q
python3 -m pytest -q tests/test_app_startup_smoke.py
python3 -m compileall app.py grade_engine tests
```
