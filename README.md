# Fabric Service Operations Analytics

[![Python quality](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml/badge.svg)](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml)

**Microsoft Fabric direction · service operations · medallion architecture · SQL analytics · DuckDB · star schema · data quality · Python 3.12 · Parquet · pytest · GitHub Actions**

A bounded DataTideHH portfolio project that prepares synthetic IT service-operations data for a later Microsoft Fabric and Power BI implementation.

The repository now contains a reproducible local Bronze/Silver/Gold pipeline plus a versioned DuckDB SQL analytics layer. It generates a deterministic 90-day operating scenario, separates valid and rejected records, publishes a Gold star schema, defines metric eligibility explicitly and produces reconciled SLA analysis before any cloud or proprietary BI artefact is claimed.

## Current status

```text
Local data contract and quality controls: implemented
Calibrated synthetic operating scenario: implemented
Local Bronze/Silver/Gold pipeline: implemented
Local Parquet star schema and KPI evidence: implemented
DuckDB SQL analytics layer: implemented
SLA breach analysis and metric contract: implemented
Cross-platform CI: implemented
Fabric workspace execution: not yet claimed
Lakehouse / OneLake objects: not yet created
Power BI semantic model and report: planned
```

This distinction is deliberate. The project implements and tests transformation and analytical logic locally without presenting hand-written placeholders as executed Fabric or Power BI artefacts.

## Business scenario

The deterministic generator models one customer environment, five operational teams and a 90-day analysis window. Category, priority and resolver-team assignment are correlated; SLA breaches influence escalation probability; reopenings occur only after closure.

The data supports analysis of:

- request volumes by priority, category and team
- SLA compliance, breach counts and breach rates
- resolution time
- escalations
- reopenings
- open backlog
- team-category concentration patterns
- data-quality failures before reporting

No customer, employee or operational production data is included. The KPI ranges are design constraints for this synthetic scenario, not claimed industry benchmarks.

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

The Medallion build fails when Bronze does not reconcile to valid plus rejected rows, when Silver valid records do not reconcile to the Gold fact table, when a Gold foreign key is unresolved or when generated evidence differs from the committed text evidence.

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

The analytics manifest verifies that:

- all grouped closed-ticket populations reconcile to 833,
- all grouped breach counts reconcile to 34,
- daily request volume reconciles to 989,
- the weighted team SLA rate equals the global 95.92%,
- every breach row is closed and has a positive resolution overrun.

The metric contract is stored in [`analytics/metric_contract.json`](analytics/metric_contract.json). The reviewable analysis is stored in [`evidence/sla_analysis.md`](evidence/sla_analysis.md).

The current evidence shows a useful count-versus-rate distinction: `business_apps` has the highest team breach count, while `network_ops` has the highest team breach rate. Application requests have the highest category breach count, while network requests have the highest category breach rate. These are concentration findings, not causal root-cause claims.

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
      v
Gold star schema + KPI evidence
      |
      v
DuckDB SQL analytics layer
+ enriched request mart
+ SLA summaries
+ daily operations
+ breach detail
      |
      v
analytics manifest + CSV/Markdown evidence
      |
      v
planned Fabric Lakehouse / Direct Lake / Power BI implementation
```

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/data-contract.md`](docs/data-contract.md)
- [`docs/local-medallion-pipeline.md`](docs/local-medallion-pipeline.md)
- [`docs/sql-analytics-layer.md`](docs/sql-analytics-layer.md)
- [`docs/fabric-adoption-plan.md`](docs/fabric-adoption-plan.md)

## Quick start

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
```

Generate the source and build both local layers:

```powershell
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
├── sla_by_team.csv
├── sla_by_category.csv
├── sla_by_priority.csv
└── analytics_manifest.json
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

1. installs DuckDB, pandas, PyArrow and quality dependencies,
2. compiles Python sources,
3. runs Ruff lint and format checks,
4. runs the complete pytest suite,
5. generates and fingerprints the deterministic 1,000-row source,
6. validates the 1,000/989/11 data-quality controls,
7. builds and verifies every Bronze/Silver/Gold output,
8. executes every SQL analytics mart,
9. reconciles grouped outputs to the Gold controls,
10. compares generated JSON and CSV evidence with the committed evidence,
11. uploads short-lived Parquet, CSV, JSON and validation artefacts.

## Scope boundaries

This repository currently does not claim:

- a deployed Fabric Lakehouse,
- OneLake persistence,
- Fabric Spark or notebook execution,
- a Data Factory pipeline,
- a Fabric SQL analytics endpoint,
- a Direct Lake semantic model,
- a Power BI report,
- production-scale service-management analytics,
- causal root-cause analysis.

The implemented DuckDB layer is a local, tested SQL analytics contract. It is not a Fabric SQL endpoint or a Power BI semantic model. Later Fabric and Power BI artefacts must reproduce the committed controls and analytical evidence.
