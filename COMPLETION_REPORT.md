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

```bash
streamlit run app.py
```

Headless startup check used during validation:

```bash
python3 -m pytest -q tests/test_app_startup_smoke.py
```

## Test

```bash
python3 -m pytest -q
python3 -m compileall app.py grade_engine tests
```

## Validation Notes

- Streamlit startup is covered with `streamlit.testing.v1.AppTest`.
- Headless startup is covered by `tests/test_app_startup_smoke.py`, which allocates a free port automatically, and was also re-verified manually on open local ports `8537` and `8538`.
- Every visible tool family is exercised through the UI path.
- Supplier search links are validated for turning and non-turning flows.
- Startup validation no longer depends on `8513` already being free on the machine.
- Kennametal search now routes through a live site-filtered catalog search instead of a dead internal search URL.
- MSC and ISCAR search links now route through live site-filtered search results instead of brittle direct catalog endpoints that returned `403` during automated validation.
- Sandvik `GC1115` now has a shop-readable description so PVD stainless and super-alloy paths do not render blank supplier text.
- Drill guidance now keeps cast-iron geometry separate from polished non-ferrous drill guidance.
- Tap warnings now stay material-relevant instead of showing super-alloy warnings on non-ferrous tap recommendations.
- Stainless light-DOC warnings now stay accurate even when finish priority is not set to finishing.
- Repeated automated test passes completed cleanly.

## Remaining Limits

- Non-turning families resolve to supplier search guidance rather than supplier-specific grade tables.
- Tap recommendations still require the machinist to confirm through-hole versus blind-hole geometry before ordering.
