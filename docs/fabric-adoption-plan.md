# Microsoft Fabric Adoption Plan

The repository is executable without a Fabric capacity. PR 1 established the source and quality contract; PR 2 implemented the complete local Bronze/Silver/Gold transformation and reconciliation logic; PR 2.1 calibrated the synthetic operating scenario; PR 2.2 adds a versioned SQL analytics contract before semantic-model and report work begins.

## Why Fabric-generated items are not hand-written yet

Fabric Git integration tracks item definitions and metadata, but Lakehouse table and file data are not stored in Git. Workspace-generated identifiers and notebook bindings should come from a real workspace rather than being invented in advance.

Official references:

- Medallion architecture in Fabric:
  https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
- Lakehouse Git integration:
  https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-git-deployment-pipelines
- Notebook source control:
  https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment

## Completed locally

### PR 1 — Repository and contract baseline

- deterministic synthetic source generator
- machine-readable data contract
- row-level validation and issue codes
- bounded intentional data-quality defects
- Ubuntu and Windows CI

### PR 2 — Local Bronze, Silver and Gold pipeline

- source-preserving Bronze Parquet with ingestion metadata
- typed Silver valid table
- auditable Silver rejection and issue tables
- Gold fact and four dimensions
- reconciled operational KPIs
- stable manifest and committed text evidence
- full cross-platform pipeline execution in CI

### PR 2.1 — Calibrated service-operations baseline

- 1,000 generated source rows across a 90-day scenario
- category, team and priority relationships
- 1,000/989/11 reconciliation controls
- explicit KPI denominators
- closed-ticket denominator for reopen rate
- documented synthetic design ranges for SLA, reopen, escalation and backlog rates
- stable full-file SHA-256 fingerprint instead of a committed generated CSV

### PR 2.2 — SQL analytics layer and SLA breach analysis

- DuckDB execution directly against local Gold Parquet tables
- versioned SQL models for enriched requests, daily operations and SLA analysis
- grouped marts by team, category, priority and team-category combination
- exactly 34 auditable SLA breach detail rows
- machine-readable metric contract with explicit eligible populations and denominators
- analytics manifest reconciled to the Gold KPI and row-count evidence
- reviewable CSV and Markdown analysis outputs
- cross-platform analytics execution in CI

## Remaining implementation sequence

### PR 3 — Semantic model and report

- define and document model relationships
- create operational DAX measures
- add a compact Power BI report
- reconcile report measures to the committed Gold and SQL analytics evidence
- capture model and report screenshots

This stage can be produced locally with Power BI Desktop. It does not by itself prove Fabric execution.

### PR 4 — Real Fabric execution and lifecycle

- create the real Fabric Lakehouse
- import or adapt the tested transformation logic in a Fabric notebook
- write Bronze, Silver and Gold Delta tables
- reproduce the local control totals, KPIs and analytical marts
- synchronize real Fabric item definitions
- verify notebook, Lakehouse and semantic-model bindings
- document workspace setup, execution and source-control boundaries

## Acceptance criteria for the first Fabric run

The Fabric implementation must reproduce the local controls:

```text
source rows:        1,000
silver valid rows:    989
silver rejected rows:  11
gold fact rows:        989
SLA breach rows:        34
```

It must also reproduce the committed KPI, foreign-key and analytics reconciliation controls. Any difference must be explained before downstream reporting is accepted.
