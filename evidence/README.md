# Verified Text Evidence

These small text files make the local Medallion controls reviewable without downloading CI artefacts:

- `medallion_manifest.json` records row counts, issue counts, reconciliation controls and KPIs.
- `service_operations_kpis.csv` exposes the Gold KPI row in a BI-friendly format.

The 1,000-row synthetic source is generated from code rather than committed as derived CSV data. Tests and GitHub Actions verify its complete SHA-256 fingerprint, regenerate both evidence files and fail when the committed evidence no longer matches the pipeline.

The KPI ranges are design constraints for this bounded synthetic scenario, not claimed industry benchmarks. Reopen rate uses closed tickets as its eligible population; open tickets cannot be reopened.
