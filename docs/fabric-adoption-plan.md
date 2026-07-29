# Microsoft Fabric Adoption Plan

The repository is executable without a Fabric capacity. PR 1 established the source and quality contract; PR 2 implements the complete local Bronze/Silver/Gold transformation and reconciliation logic that later Fabric work must reproduce.

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

- deterministic synthetic raw CSV
- machine-readable data contract
- row-level validation and issue codes
- 100/89/11 control totals
- Ubuntu and Windows CI

### PR 2 — Local Bronze, Silver and Gold pipeline

- source-preserving Bronze Parquet with ingestion metadata
- typed Silver valid table
- auditable Silver rejection and issue tables
- Gold fact and four dimensions
- reconciled operational KPIs
- stable manifest and committed text evidence
- full cross-platform pipeline execution in CI

## Remaining implementation sequence

### PR 3 — Semantic model and report

- define and document model relationships
- create operational DAX measures
- add a compact Power BI report
- reconcile report measures to the committed Gold KPI evidence
- capture model and report screenshots

This stage can be produced locally with Power BI Desktop. It does not by itself prove Fabric execution.

### PR 4 — Real Fabric execution and lifecycle

- create the real Fabric Lakehouse
- import or adapt the tested transformation logic in a Fabric notebook
- write Bronze, Silver and Gold Delta tables
- reproduce the local control totals and KPIs
- synchronize real Fabric item definitions
- verify notebook, Lakehouse and semantic-model bindings
- document workspace setup, execution and source-control boundaries

## Acceptance criteria for the first Fabric run

The Fabric implementation must reproduce the local controls:

```text
source rows:          100
silver valid rows:     89
silver rejected rows:  11
gold fact rows:        89
```

It must also reproduce the committed KPI and foreign-key controls. Any difference must be explained before downstream reporting is accepted.
