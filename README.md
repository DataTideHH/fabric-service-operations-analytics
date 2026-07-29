# Fabric Service Operations Analytics

[![Python quality](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml/badge.svg)](https://github.com/DataTideHH/fabric-service-operations-analytics/actions/workflows/python-quality.yml)

**Microsoft Fabric direction · service operations · medallion architecture · star schema · data quality · Python 3.12 · pandas · Parquet · pytest · GitHub Actions**

A bounded DataTideHH portfolio project that prepares synthetic IT service-operations data for a later Microsoft Fabric implementation.

The repository now contains a reproducible local Bronze/Silver/Gold pipeline. It preserves raw records with ingestion metadata, separates typed valid records from auditable rejections, publishes a small star schema and reconciles operational KPIs before any cloud resources are used.

## Current status

```text
Local data contract and quality controls: implemented
Local Bronze/Silver/Gold pipeline: implemented
Local Parquet star schema and KPI evidence: implemented
Cross-platform CI: implemented
Fabric workspace execution: not yet claimed
Lakehouse / OneLake objects: not yet created
Power BI semantic model and report: planned
```

This distinction is deliberate. The project implements and tests the transformation logic locally without presenting hand-written placeholders as executed Fabric artefacts.

## Business scenario

The synthetic dataset represents service requests handled by operational teams. It supports analysis of:

- request volumes by priority, category and team
- SLA compliance
- resolution time
- escalations
- reopenings
- open backlog
- data-quality failures before reporting

No customer, employee or operational production data is included.

## Verified controls

### Data quality and reconciliation

| Control | Verified value |
|---|---:|
| Bronze source rows | 100 |
| Silver valid rows | 89 |
| Silver rejected rows | 11 |
| Silver issue records | 11 |
| Gold fact rows | 89 |
| Duplicate identifier occurrences | 2 |
| Date dimension rows | 69 |
| Team dimension rows | 5 |
| Category dimension rows | 5 |
| Priority dimension rows | 4 |

The pipeline fails when Bronze does not reconcile to valid plus rejected rows, when Silver valid records do not reconcile to the Gold fact table, or when a Gold foreign key is unresolved.

### Gold KPI evidence

| KPI | Verified value |
|---|---:|
| Total accepted requests | 89 |
| Closed requests | 73 |
| Open backlog | 16 |
| SLA-met requests | 31 |
| SLA compliance rate | 42.47% |
| Average resolution time | 1,653.75 minutes |
| Median resolution time | 1,320 minutes |
| Escalated requests | 10 |
| Escalation rate | 11.24% |
| Reopened requests | 19 |
| Reopen rate | 21.35% |

The committed text evidence is stored in [`evidence/`](evidence/) and is regenerated and compared in CI.

## Implemented local architecture

```text
synthetic raw CSV
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

See [`docs/architecture.md`](docs/architecture.md), [`docs/local-medallion-pipeline.md`](docs/local-medallion-pipeline.md) and [`docs/fabric-adoption-plan.md`](docs/fabric-adoption-plan.md).

## Quick start

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
```

Build all local layers:

```powershell
python -m service_operations build-medallion `
  --input "data/raw/service_requests.csv" `
  --contract "contracts/service_requests.contract.json" `
  --output ".ci-output/medallion"
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
python -m service_operations build-medallion \
  --input data/raw/service_requests.csv \
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

## Reproduce the source fixture

```bash
python -m service_operations generate \
  --output .ci-output/generated-service-requests.csv
```

The test suite verifies that generated bytes match the committed source fixture on Ubuntu and Windows.

## Repository structure

```text
fabric-service-operations-analytics/
├── .github/workflows/python-quality.yml
├── contracts/service_requests.contract.json
├── data/raw/service_requests.csv
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
5. regenerates and byte-compares the synthetic source fixture
6. validates the 100/89/11 data-quality controls
7. builds every local Bronze/Silver/Gold output
8. verifies row reconciliation, foreign keys, KPIs and committed evidence
9. uploads short-lived Parquet, CSV and JSON evidence

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
