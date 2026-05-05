# CNC Tool Engine

`CNC Tool Engine` is a Streamlit-based shop-support recommendation app for common CNC tooling decisions. It gives operators and programmers a quick starting point for material-group-driven guidance, tool family selection, and grade behavior without rewriting catalog data or replacing supplier documentation.

## What This App Does

The app helps generate practical starting-point recommendations across these current modules:

- Turning
- Drilling
- Endmill
- Face Mill
- Grooving
- Threading
- Burnishing
- Workholding
- Catalog Explorer

Under the hood, the app uses the modular `grade_engine/` package for grade behavior resolution and `tool_data/` JSON files for catalog-style reference data.

## Install

1. Create and activate a virtual environment.
2. Install the runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. If you want to run tests, install the development dependencies too:

```powershell
python -m pip install -r requirements-dev.txt
```

## Run

Start the Streamlit app from the repo root:

```powershell
streamlit run app.py
```

## Validation Commands

Use these commands from the repo root to verify the app and grade engine baseline:

```powershell
python -m compileall .
pytest
python tools/engine_health_report.py
```

## Project Structure

- `app.py`: Streamlit UI and module navigation
- `grade_engine/`: Recommendation and grade-behavior logic
- `tool_data/`: JSON catalog, lookup, and validation data
- `tests/`: Smoke and validation coverage for the grade engine

## Important Use Note

This app provides shop-support recommendation guidance only. It is not final manufacturer-certified cutting data, and it should not replace supplier catalogs, tooling application engineering, machine limitations, or your shop's approved process standards.
