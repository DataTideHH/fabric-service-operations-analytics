# Verified Text Evidence

These small text files make the local Medallion controls reviewable without downloading CI artefacts:

- `medallion_manifest.json` records row counts, issue counts, reconciliation controls and KPIs.
- `service_operations_kpis.csv` exposes the Gold KPI row in a BI-friendly format.

The test suite and GitHub Actions regenerate both results and fail when the committed evidence no longer matches the pipeline.
