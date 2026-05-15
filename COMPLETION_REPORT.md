# Completion Report

## Scope Completed

The app now returns live recommendations and supplier search output for:

- turning inserts
- grooving inserts
- threading inserts
- drills
- endmills
- face mills
- taps
- reamers

## Run

Windows PowerShell:

```powershell
py -m streamlit run app.py
```

Linux / macOS:

```bash
python3 -m streamlit run app.py
```

Headless startup check used during validation:

Windows PowerShell:

```powershell
py -m pytest -q tests/test_app_startup_smoke.py
```

Linux / macOS:

```bash
python3 -m pytest -q tests/test_app_startup_smoke.py
```

## Test

Windows PowerShell:

```powershell
py -m pytest -q
py -m compileall app.py grade_engine tests
```

Linux / macOS:

```bash
python3 -m pytest -q
python3 -m compileall app.py grade_engine tests
```

## Validation Notes

- Streamlit startup is covered by both `streamlit.testing.v1.AppTest` and the subprocess-based free-port smoke test in `tests/test_app_startup_smoke.py`.
- Recommendations now render live without a one-shot build button.
- Threading now captures thread profile plus internal or external direction.
- Tap and reamer flows now capture hole type so the starter callout and supplier search reflect through-hole versus blind-hole work.
- Validation coverage now locks down family-specific starter logic for full-profile threading, through-hole tapping, hardened-material reaming, and non-ferrous endmill guidance.
- Supplier cards now show process-appropriate labels and the actual catalog search query instead of implying every family maps to an exact grade.
- The optional `Show internal logic key` control is covered by UI regression testing.
- Every visible tool family is exercised through the UI path and must render the recommendation, starter setup, behavior readout, and supplier search sections.
- Supplier search links are validated for turning and non-turning flows.
- Startup validation no longer depends on `8513` already being free on the machine.
- Kennametal search now routes through a live site-filtered catalog search instead of a dead internal search URL.
- MSC and ISCAR search links now route through live site-filtered search results instead of brittle direct catalog endpoints that returned `403` during automated validation.
- Sandvik `GC1115` now has a shop-readable description so PVD stainless and super-alloy paths do not render blank supplier text.
- Drill guidance now keeps cast-iron geometry separate from polished non-ferrous drill guidance.
- Tap warnings now stay material-relevant instead of showing super-alloy warnings on non-ferrous tap recommendations.
- Stainless light-DOC warnings now stay accurate even when finish priority is not set to finishing.
- Repeated automated test passes completed cleanly: two consecutive `32 passed` full-suite runs, a clean `5 passed` startup and UI smoke run, and a clean `python3 -m compileall app.py grade_engine tests`.

## Remaining Limits

- Non-turning families resolve to supplier search guidance rather than supplier-specific grade tables.
- Tap recommendations still require the machinist to confirm through-hole versus blind-hole geometry before ordering.
