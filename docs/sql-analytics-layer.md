# SQL Analytics Layer

## Purpose

The SQL analytics layer turns the tested Gold Parquet star schema into transparent, versioned analytical marts before Power BI or Microsoft Fabric is introduced. DuckDB executes the SQL locally on Windows, macOS and Linux.

This keeps metric logic reviewable in Git and prevents a later BI report from becoming the first place where eligibility rules, denominators and aggregation logic are defined.

## Command

```bash
python -m service_operations build-analytics \
  --medallion .ci-output/medallion \
  --sql-dir analytics/sql \
  --output .ci-output/analytics
```

## Versioned SQL models

| SQL model | Grain and purpose |
|---|---|
| `service_requests_enriched.sql` | One accepted request with joined team, category, priority and date labels |
| `sla_by_team.sql` | One closed-ticket summary row per resolver team |
| `sla_by_category.sql` | One closed-ticket summary row per request category |
| `sla_by_priority.sql` | One closed-ticket summary row per priority |
| `sla_by_team_category.sql` | One closed-ticket summary row per observed team-category combination |
| `daily_service_operations.sql` | One row per request creation date |
| `sla_breach_details.sql` | One row per SLA-breached closed request |

## Metric semantics

The machine-readable metric contract is stored in [`analytics/metric_contract.json`](../analytics/metric_contract.json).

```text
SLA compliance = SLA-met closed tickets / closed tickets
SLA breach rate = SLA-breached closed tickets / closed tickets
Reopen rate = closed tickets reopened at least once / closed tickets
Escalation rate = escalated accepted tickets / accepted tickets
Closed escalation rate = escalated closed tickets / closed tickets
Backlog rate = open accepted tickets / accepted tickets
```

Every grouped output includes its denominator as a count. This prevents a high-volume team from appearing worse solely because it owns more tickets.

## Reconciliation controls

The analytics build fails unless all controls pass:

```text
Enriched requests = Gold fact rows
Breach details = global SLA breach count
Team closed totals = global closed total
Category closed totals = global closed total
Priority closed totals = global closed total
Team-category closed totals = global closed total
Daily request totals = global accepted total
Weighted team SLA rate = global SLA compliance rate
Every breach row is closed
Every breach overrun is positive
```

For the committed scenario, the analytical population is:

```text
Accepted requests: 989
Closed requests: 833
SLA-met requests: 799
SLA breaches: 34
```

## Output contract

The output directory contains Parquet marts for downstream tools and small CSV/JSON evidence for review:

```text
analytics/
├── service_requests_enriched.parquet
├── sla_by_team.parquet
├── sla_by_category.parquet
├── sla_by_priority.parquet
├── sla_by_team_category.parquet
├── daily_service_operations.parquet
├── sla_breach_details.parquet
├── sla_by_team.csv
├── sla_by_category.csv
├── sla_by_priority.csv
└── analytics_manifest.json
```

## Interpretation boundary

The marts show where SLA breaches concentrate and which dimensions are associated with them. They do not prove root cause. The synthetic source has no cause codes, waiting-state history, assignment changes, supplier dependencies, linked changes or linked problem records.

## Later Power BI use

Power BI can later consume either the Gold star schema or the prepared marts. The SQL layer is not presented as a Power BI semantic model, DAX implementation, Direct Lake model or Fabric execution. It is the testable analytical contract those later artefacts must reproduce.
