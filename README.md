# Fabric Service Operations Analytics

[![Python quality](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml/badge.svg)](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml)

**Microsoft Fabric direction · service operations · medallion architecture · SQL analytics · process intelligence · data quality · DuckDB · Python 3.12 · Parquet · pytest · GitHub Actions**

A bounded DataTideHH portfolio project that prepares synthetic IT service-operations data for later Microsoft Fabric, Power BI and Process Mining implementations.

The repository contains a reproducible local Bronze/Silver/Gold pipeline, a versioned DuckDB SQL analytics layer and a deterministic process-intelligence layer. It generates a controlled 90-day operating scenario, separates valid and rejected records, publishes a Gold star schema, defines metric eligibility explicitly, reconciles SLA analysis and derives a process-mining-ready event log without claiming observed production history.

## Related writing

[**The Dashboard Wasn't the Hard Part: Why KPI Definitions Matter**](https://medium.com/@tobiaswietelmann/the-dashboard-wasnt-the-hard-part-why-kpi-definitions-matter-c762cebae500) — a project-based article on KPI definitions, denominator choices, count vs. rate, aggregation effects, data quality and analytical validation using reproducible outputs from this repository.

## Current status

```text
Local data contract and quality controls: implemented
Calibrated synthetic operating scenario: implemented
Local Bronze/Silver/Gold pipeline: implemented
Local Parquet star schema and KPI evidence: implemented
DuckDB SQL analytics layer: implemented
SLA breach analysis and metric contract: implemented
Derived process event log: implemented
Process variants and transition analysis: implemented
Escalation and reopening path analysis: implemented
Cross-platform CI and committed evidence: implemented
Fabric workspace execution: not yet claimed
Lakehouse / OneLake objects: not yet created
Power BI semantic model and report: planned
Observed production event history: not claimed
```

This distinction is deliberate. The project implements and tests transformation, analytical and process logic locally without presenting hand-written placeholders as executed Fabric, Power BI or production Process Mining artefacts.

## Business scenario

The deterministic generator models one customer environment, five operational teams and a 90-day analysis window. Category, priority and resolver-team assignment are correlated; SLA breaches influence escalation probability; reopenings occur only after closure.

The data supports analysis of:

- request volume by priority, category and team
- SLA compliance, breach counts and breach rates
- resolution time, escalations, reopenings and backlog
- team-category concentration patterns
- data-quality failures before reporting
- process variants and transition waiting-time concentrations
- escalated and reopened exception paths

No customer, employee or operational production data is included. KPI ranges and process timings are design constraints for this synthetic scenario, not claimed industry benchmarks.

## Verified pipeline controls

### Data quality and reconciliation

| Control | Verified value |
|---|---:|
| Generated source rows | 1,000 |
| Bronze source rows | 1,000 |
| Silver valid rows | 989 |
| Silver rejected rows | 11 |
| Silver issue records | 11 |
| Gold fact rows | 989 |
| Duplicate identifier occurrences | 2 |
| Date dimension rows | 91 |
| Team dimension rows | 5 |
| Category dimension rows | 5 |
| Priority dimension rows | 4 |

The Medallion build fails when Bronze does not reconcile to valid plus rejected rows, when Silver valid records do not reconcile to the Gold fact table, when a Gold foreign key is unresolved or when generated evidence differs from committed evidence.

### Gold KPI evidence

| KPI | Verified value |
|---|---:|
| Total accepted requests | 989 |
| Closed requests | 833 |
| Open backlog | 156 |
| Open backlog rate | 15.77% |
| SLA-met requests | 799 |
| SLA breaches | 34 |
| SLA compliance rate | 95.92% |
| Average resolution time | 835.84 minutes |
| Median resolution time | 694 minutes |
| Escalated requests | 85 |
| Escalation rate | 8.59% |
| Reopened requests | 48 |
| Reopen rate | 5.76% |

KPI denominators are explicit:

```text
SLA compliance = SLA-met closed tickets / closed tickets
SLA breach rate = SLA-breached closed tickets / closed tickets
Reopen rate = closed tickets reopened at least once / closed tickets
Escalation rate = escalated accepted tickets / accepted tickets
Backlog rate = open accepted tickets / accepted tickets
```

## SQL analytics layer

DuckDB reads the generated Gold Parquet tables directly and executes the versioned SQL in [`analytics/sql/`](analytics/sql/).

| Mart | Verified rows |
|---|---:|
| Enriched accepted requests | 989 |
| SLA by team | 5 |
| SLA by category | 5 |
| SLA by priority | 4 |
| SLA by team and category | 15 |
| Daily service operations | 90 |
| SLA breach details | 34 |

The analytics manifest verifies that grouped closed-ticket populations, breach counts, daily volume and weighted SLA results reconcile to the Gold controls. The layer distinguishes count from rate and identifies concentration patterns without claiming causal root cause.

The metric contract is stored in [`analytics/metric_contract.json`](analytics/metric_contract.json). Reviewable analysis is stored in [`evidence/sla_analysis.md`](evidence/sla_analysis.md).

## Process-intelligence layer

The process layer converts the 989 typed Silver records into an ordered event log with case identifier, activity and timestamp columns.

| Output | Verified rows |
|---|---:|
| Process cases | 989 |
| Event log | 3,831 |
| Process variants | 7 |
| Transition types | 7 |
| Ranked bottleneck candidates | 7 |
| Exception path types | 3 |

Verified case populations:

```text
closed cases:          833
open cases:            156
escalated cases:        85
reopened cases:         48
reopen occurrences:     51
```

The leading standard variant contains 714 cases:

```text
ticket_created > team_assigned > resolution_recorded > ticket_closed
```

The largest derived waiting-time concentration is `team_assigned > resolution_recorded`, covering 758 transitions with an average derived wait of 712.59 minutes.

### Interpretation boundary

The source model contains ticket creation, final closure, escalation status and reopening count. It does not contain observed status-history timestamps. Intermediate events are therefore deterministic scenario derivations marked with:

```text
event_origin = derived_synthetic_scenario
```

The event log supports process-analysis practice and later Process Mining integration design. It is not represented as production telemetry and does not support causal root-cause claims.

See [`docs/process-intelligence.md`](docs/process-intelligence.md).

## Implemented local architecture

```text
deterministic synthetic generator
      |
      v
generated service_requests.csv
      |
      v
Bronze Parquet
      |
      v
contract validation
      |
      +-------------------------------+
      |                               |
      v                               v
Silver valid Parquet             Silver rejected + issue audit
      |
      +-------------------------------+
      |                               |
      v                               v
Gold star schema + KPIs          derived process event log
      |                           + cases / variants
      v                           + transitions / bottlenecks
DuckDB SQL analytics             + exception paths
      |                               |
      v                               v
analytics evidence               process evidence
      |
      v
planned Fabric Lakehouse / Direct Lake / Power BI implementation
```

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/data-contract.md`](docs/data-contract.md)
- [`docs/local-medallion-pipeline.md`](docs/local-medallion-pipeline.md)
- [`docs/sql-analytics-layer.md`](docs/sql-analytics-layer.md)
- [`docs/process-intelligence.md`](docs/process-intelligence.md)
- [`docs/fabric-adoption-plan.md`](docs/fabric-adoption-plan.md)

## Quick start

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest

python -m service_operations generate `
  --output ".ci-output\service_requests.csv"

python -m service_operations build-medallion `
  --input ".ci-output\service_requests.csv" `
  --contract "contracts\service_requests.contract.json" `
  --output ".ci-output\medallion"

python -m service_operations build-analytics `
  --medallion ".ci-output\medallion" `
  --sql-dir "analytics\sql" `
  --output ".ci-output\analytics"

python -m service_operations build-process-intelligence `
  --input ".ci-output\service_requests.csv" `
  --contract "contracts\service_requests.contract.json" `
  --output ".ci-output\process-intelligence"
```

### macOS and Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest

python -m service_operations generate \
  --output .ci-output/service_requests.csv

python -m service_operations build-medallion \
  --input .ci-output/service_requests.csv \
  --contract contracts/service_requests.contract.json \
  --output .ci-output/medallion

python -m service_operations build-analytics \
  --medallion .ci-output/medallion \
  --sql-dir analytics/sql \
  --output .ci-output/analytics

python -m service_operations build-process-intelligence \
  --input .ci-output/service_requests.csv \
  --contract contracts/service_requests.contract.json \
  --output .ci-output/process-intelligence
```

## Generated outputs

```text
medallion/
├── bronze/service_requests.parquet
├── silver/service_requests_valid.parquet
├── silver/service_requests_rejected.parquet
├── silver/service_request_issues.parquet
├── gold/fact_service_requests.parquet
├── gold/dim_date.parquet
├── gold/dim_team.parquet
├── gold/dim_category.parquet
├── gold/dim_priority.parquet
├── gold/service_operations_kpis.csv
└── medallion_manifest.json

analytics/
├── service_requests_enriched.parquet
├── sla_by_team.parquet
├── sla_by_category.parquet
├── sla_by_priority.parquet
├── sla_by_team_category.parquet
├── daily_service_operations.parquet
├── sla_breach_details.parquet
├── review CSV files
└── analytics_manifest.json

process-intelligence/
├── event_log.parquet
├── event_log.csv
├── process_cases.parquet
├── process_cases.csv
├── process_variants.parquet
├── process_variants.csv
├── transition_performance.parquet
├── transition_performance.csv
├── bottlenecks.parquet
├── bottlenecks.csv
├── exception_paths.parquet
├── exception_paths.csv
└── process_intelligence_manifest.json
```

## Deterministic source evidence

The generated source is not committed as a large derived CSV. Tests and GitHub Actions verify its complete SHA-256 fingerprint on Ubuntu and Windows:

```text
292ed8fb2857e3927936a5b3ca002492b146875d04baee77a9322de287db8914
```

See [`data/README.md`](data/README.md).

## Repository structure

```text
fabric-service-operations-analytics/
├── .github/workflows/python-quality.yml
├── analytics/
│   ├── metric_contract.json
│   └── sql/
├── contracts/service_requests.contract.json
├── data/README.md
├── docs/
├── evidence/
├── fabric/README.md
├── src/service_operations/
├── tests/
├── pyproject.toml
└── README.md
```

## Quality automation

The GitHub Actions matrix runs Python 3.12 on Ubuntu 24.04 and Windows 2025. Each job:

1. installs runtime and quality dependencies
2. compiles Python sources
3. runs Ruff lint and format checks
4. runs the complete pytest suite
5. generates and fingerprints the deterministic source
6. validates the 1,000/989/11 data-quality controls
7. builds and verifies every Bronze/Silver/Gold output
8. executes and reconciles every SQL analytics mart
9. builds the event log, variants, transitions and exception paths
10. compares generated JSON and CSV evidence with committed evidence
11. uploads short-lived Parquet, CSV, JSON and validation artefacts

## Scope boundaries

This repository currently does not claim:

- a deployed Fabric Lakehouse or OneLake persistence
- Fabric Spark, notebook or Data Factory execution
- a Fabric SQL analytics endpoint
- a Direct Lake semantic model
- a completed Power BI report
- production-scale service-management analytics
- observed production event history
- object-centric Process Mining
- causal process or SLA root-cause analysis

The implemented layers are local, tested analytical contracts. Later Fabric, Power BI and Process Mining artefacts must reproduce the committed controls and evidence rather than replace them with unsupported claims.
