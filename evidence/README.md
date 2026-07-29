# Verified Text Evidence

These small text files make the local Medallion and SQL analytics controls reviewable without downloading CI artefacts:

- `medallion_manifest.json` records Bronze/Silver/Gold row counts, issue counts, reconciliation controls and global KPIs.
- `service_operations_kpis.csv` exposes the Gold KPI row in a BI-friendly format.
- `analytics_manifest.json` reconciles every SQL analytics mart to the Gold population.
- `sla_by_team.csv`, `sla_by_category.csv` and `sla_by_priority.csv` expose the principal SLA analysis outputs.
- `sla_analysis.md` summarizes the concentration findings and their interpretation boundary.

The 1,000-row synthetic source is generated from code rather than committed as derived CSV data. Tests and GitHub Actions verify its complete SHA-256 fingerprint, rebuild the Medallion and SQL analytics layers, regenerate the text evidence and fail when the committed evidence no longer matches.

The KPI ranges are design constraints for this bounded synthetic scenario, not claimed industry benchmarks. Reopen rate uses closed tickets as its eligible population; open tickets cannot be reopened. The SLA analysis identifies concentration patterns but does not claim root cause.
