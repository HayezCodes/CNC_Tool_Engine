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

## Brand Intelligence Layer

The brand intelligence layer provides family-level tooling guidance for practical brand and tool-family selection by operation, ISO material group, and shop priority. It is designed to help programmers choose likely tooling families to investigate.

- Brand Intelligence: broad brand strengths, shop-use notes, source status, and recommended engine use.
- Endmill Families: endmill-only family guidance for general milling, dynamic/adaptive milling, value tooling, and specialty cutters.
- Insert/Grade Families: broad insert brand behavior tags for production turning, toughness, wear-resistance, chipbreaker direction, and general insert use.
- Problem Solver: converts common shop problems like chatter, poor finish, short tool life, small-bore access, value sourcing, dynamic milling, specialty features, and production turning into practical recommendation directions.
- Tool Lookup Integration: search terms that match known brands, operations, or tooling families can show a supplemental family-level Brand Intelligence panel below the normal lookup results.

This layer does not replace manufacturer catalogs, does not provide certified speeds/feeds, and does not claim exact catalog numbers, dimensions, grade equivalency, or manufacturer-approved cutting data.

## Catalog Ingestion Pipeline

The catalog ingestion pipeline is a staged foundation for future manufacturer tooling data work. It uses official manufacturer catalog/resource pages first, keeps staged records untrusted until reviewed, and does not import exact feeds/speeds into staged data yet.

First staged manufacturer data: Helical Solutions endmill family records.

Staged records live separately from production recommendation data. Reviewed records can later feed the Brand Intelligence layer only after source citation and shop-safe validation.

Reviewed catalog records are still family-level unless cutting data is separately validated.

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
