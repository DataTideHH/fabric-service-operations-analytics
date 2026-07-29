# Fabric Service Operations Analytics

[![Python quality](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml/badge.svg)](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml)

**Microsoft Fabric direction · service operations · medallion architecture · star schema · data quality · Python 3.12 · pandas · Parquet · pytest · GitHub Actions**

A bounded DataTideHH portfolio project that prepares synthetic IT service-operations data for a later Microsoft Fabric implementation.

The repository contains a reproducible local Bronze/Silver/Gold pipeline. It generates a deterministic 90-day operating scenario, preserves raw records with ingestion metadata, separates typed valid records from auditable rejections, publishes a small star schema and reconciles operational KPIs before any cloud resources are used.

## Current status

```text
Local data contract and quality controls: implemented
Calibrated synthetic operating scenario: implemented
Local Bronze/Silver/Gold pipeline: implemented
Local Parquet star schema and KPI evidence: implemented
Cross-platform CI: implemented
Fabric workspace execution: not yet claimed
Lakehouse / OneLake objects: not yet created
Power BI semantic model and report: planned
```

This distinction is deliberate. The project implements and tests the transformation logic locally without presenting hand-written placeholders as executed Fabric artefacts.

## Business scenario

The deterministic generator models one customer environment, five operational teams and a 90-day analysis window. Category, priority and team assignment are correlated; SLA breaches influence escalation probability; reopenings occur only after closure.

The dataset supports analysis of:

- request volumes by priority, category and team
- SLA compliance and breach concentration
- resolution time
- escalations
- reopenings
- open backlog
- data-quality failures before reporting

No customer, employee or operational production data is included. The documented KPI ranges are design constraints for this synthetic scenario, not claimed industry benchmarks.

## Verified controls

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

The pipeline fails when Bronze does not reconcile to valid plus rejected rows, when Silver valid records do not reconcile to the Gold fact table, when a Gold foreign key is unresolved or when generated evidence differs from the committed text evidence.

### Gold KPI evidence

| KPI | Verified value |
|---|---:|
| Total accepted requests | 989 |
| Closed requests | 833 |
| Open backlog | 156 |
| Open backlog rate | 15.77% |
| SLA-met requests | 799 |
| SLA compliance rate | 95.92% |
| Average resolution time | 835.84 minutes |
| Median resolution time | 694 minutes |
| Escalated requests | 85 |
| Escalation rate | 8.59% |
| Reopened requests | 48 |
| Reopen rate | 5.76% |

KPI denominators are explicit:

```text
SLA compliance = SLA-met closed tickets / SLA-eligible closed tickets
Reopen rate     = closed tickets reopened at least once / closed tickets
Escalation rate = escalated accepted tickets / accepted tickets
Backlog rate    = open accepted tickets / accepted tickets
```

The committed text evidence is stored in [`evidence/`](evidence/) and regenerated in CI.

## Implemented local architecture

```text
deterministic synthetic generator
      |
      v
generated service_requests.csv
      |
      v
Bronze Parquet
source-shaped values + source row + file + batch metadata
      |
      v
contract validation
      |
      +-------------------------------+
      |                               |
      v                               v
Silver valid Parquet             Silver rejected Parquet
strictly typed records           raw values + rejection reasons
      |                               |
      |                               +--> issue-level audit Parquet
      v
Gold star schema
fact_service_requests
+ dim_date
+ dim_team
+ dim_category
+ dim_priority
      |
      v
reconciled KPI CSV + manifest JSON
      |
      v
planned Fabric Lakehouse / Direct Lake / Power BI implementation
```

See [`docs/architecture.md`](docs/architecture.md), [`docs/data-contract.md`](docs/data-contract.md), [`docs/local-medallion-pipeline.md`](docs/local-medallion-pipeline.md) and [`docs/fabric-adoption-plan.md`](docs/fabric-adoption-plan.md).

## Quick start

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
```

Generate the deterministic source and build all local layers:

```powershell
python -m service_operations generate `
  --output ".ci-output\service_requests.csv"

python -m service_operations build-medallion `
  --input ".ci-output\service_requests.csv" `
  --contract "contracts\service_requests.contract.json" `
  --output ".ci-output\medallion"
```

### macOS and Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
```

```bash
python -m service_operations generate \
  --output .ci-output/service_requests.csv

python -m service_operations build-medallion \
  --input .ci-output/service_requests.csv \
  --contract contracts/service_requests.contract.json \
  --output .ci-output/medallion
```

The output directory contains:

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
├── contracts/service_requests.contract.json
├── data/README.md
├── docs/
│   ├── architecture.md
│   ├── data-contract.md
│   ├── data-quality-rules.md
│   ├── fabric-adoption-plan.md
│   └── local-medallion-pipeline.md
├── evidence/
│   ├── medallion_manifest.json
│   └── service_operations_kpis.csv
├── fabric/README.md
├── src/service_operations/
├── tests/
├── pyproject.toml
└── README.md
```

## Quality automation

The GitHub Actions matrix runs Python 3.12 on Ubuntu 24.04 and Windows 2025. Each job:

1. installs pandas, PyArrow and the quality dependencies
2. compiles Python sources
3. runs Ruff lint and format checks
4. runs the complete pytest suite
5. generates the deterministic 1,000-row source
6. verifies the complete source fingerprint
7. validates the 1,000/989/11 data-quality controls
8. builds every local Bronze/Silver/Gold output
9. verifies row reconciliation, foreign keys, KPI ranges and committed evidence
10. uploads short-lived Parquet, CSV and JSON evidence

## Scope boundaries

This repository currently does not claim:

- a deployed Fabric Lakehouse
- OneLake persistence
- Fabric Spark or notebook execution
- a Data Factory pipeline
- a SQL analytics endpoint
- a Direct Lake semantic model
- a Power BI report
- production-scale service management analytics

The local pipeline is the tested implementation contract that later Fabric artefacts must reproduce.
