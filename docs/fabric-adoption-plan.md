# Microsoft Fabric Adoption Plan

The repository is executable without a Fabric capacity. Each merged pull request establishes a tested local contract that later Fabric and Power BI artefacts must reproduce.

## Why Fabric-generated items are not hand-written yet

Fabric Git integration tracks item definitions and metadata, but Lakehouse table and file data are not stored in Git. Workspace-generated identifiers and notebook bindings should come from a real workspace rather than being invented in advance.

Official references:

- Medallion architecture in Fabric:
  https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
- Lakehouse Git integration:
  https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-git-deployment-pipelines
- Notebook source control:
  https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment

## Completed GitHub pull-request sequence

### PR 1 — Repository and contract baseline

- deterministic synthetic source generator
- machine-readable data contract
- row-level validation and stable issue codes
- bounded intentional data-quality defects
- Ubuntu and Windows CI

### PR 2 — Local Bronze, Silver and Gold pipeline

- source-preserving Bronze Parquet with ingestion metadata
- typed Silver valid table
- auditable Silver rejection and issue tables
- Gold fact and four dimensions
- reconciled operational KPIs
- stable manifest and committed text evidence

### PR 3 — Calibrated service-operations baseline

- 1,000 generated source rows across a 90-day scenario
- category, team and priority relationships
- 1,000/989/11 reconciliation controls
- explicit KPI denominators
- documented synthetic design ranges
- stable full-file SHA-256 fingerprint

### PR 4 — SQL analytics layer and SLA breach analysis

- DuckDB execution directly against local Gold Parquet tables
- versioned SQL models for enriched requests, daily operations and SLA analysis
- grouped marts by team, category, priority and team-category combination
- exactly 34 auditable SLA breach rows
- machine-readable metric contract
- cross-platform analytics execution and evidence reconciliation

### PR 5 — Process-intelligence event layer

- deterministic event log over the 989 valid cases
- process variants and case-level process summaries
- transition wait-time statistics
- ranked waiting-time concentrations
- escalation and reopening path analysis
- event, case and exception reconciliation controls
- explicit distinction between derived scenario events and observed production history
- CSV and Parquet outputs prepared for later Process Mining integration

## Remaining implementation sequence

### PR 6 — Semantic model and Power BI report

- define and document model relationships
- create operational DAX measures
- add a compact Power BI report
- reconcile report measures to committed Gold, SQL and process evidence
- capture reviewed model and report screenshots

This stage can be produced locally with Power BI Desktop. It does not by itself prove Fabric execution.

### PR 7 — Real Fabric execution and lifecycle

- create the real Fabric Lakehouse
- import or adapt the tested transformation logic in a Fabric notebook
- write Bronze, Silver and Gold Delta tables
- reproduce local row counts, KPIs, SQL marts and process controls
- synchronize real Fabric item definitions
- verify notebook, Lakehouse and semantic-model bindings
- document workspace setup, execution and source-control boundaries

## Acceptance criteria for the first Fabric run

The Fabric implementation must reproduce the local controls:

```text
source rows:          1,000
silver valid rows:      989
silver rejected rows:    11
gold fact rows:          989
SLA breach rows:          34
process event rows:    3,831
process variants:          7
```

It must also reproduce the committed KPI, foreign-key, analytics and process-intelligence reconciliation controls. Any difference must be explained before downstream reporting is accepted.
