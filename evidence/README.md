# Verified Text Evidence

These small text files make the local Medallion, SQL analytics and process-intelligence controls reviewable without downloading CI artefacts:

- `medallion_manifest.json` records Bronze/Silver/Gold row counts, issue counts, reconciliation controls and global KPIs.
- `service_operations_kpis.csv` exposes the Gold KPI row in a BI-friendly format.
- `analytics_manifest.json` reconciles every SQL analytics mart to the Gold population.
- `sla_by_team.csv`, `sla_by_category.csv` and `sla_by_priority.csv` expose the principal SLA analysis outputs.
- `sla_analysis.md` summarizes the concentration findings and their interpretation boundary.
- `ai_service_operations_snapshot.json` is the schema-validated, fingerprinted handoff consumed by the downstream Spring AI project.
- `process_intelligence_manifest.json` reconciles cases, events, variants, transitions and exception paths to the Silver population.
- `process_variants.csv` exposes the seven derived process variants.
- `transition_performance.csv` exposes transition counts and waiting-time distributions.
- `bottlenecks.csv` ranks derived waiting-time concentrations without claiming causal root cause.
- `exception_paths.csv` compares escalated and reopened case paths.

The 1,000-row synthetic source is generated from code rather than committed as derived CSV data. Tests and GitHub Actions verify its complete SHA-256 fingerprint, rebuild all local layers, regenerate the text evidence and fail when committed evidence no longer matches.

The KPI ranges are design constraints for this bounded synthetic scenario, not claimed industry benchmarks. Reopen rate uses closed tickets as its eligible population; open tickets cannot be reopened. The SLA analysis identifies concentration patterns but does not claim root cause.

Intermediate process-event timestamps are deterministic scenario derivations. They support process-analysis and Process Mining preparation but are not represented as observed production history.

The AI handoff is generated from the committed analytics manifest, team SLA evidence and metric contract. Its source revision identifies the exact evidence baseline; the consumer commits a copy rather than reading this repository at runtime.
