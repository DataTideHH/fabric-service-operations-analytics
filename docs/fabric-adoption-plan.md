# Microsoft Fabric Adoption Plan

PR 1 is deliberately executable without a Fabric capacity. It establishes the data and quality contract that later Fabric work must reproduce.

## Why Fabric-generated items are not hand-written yet

Fabric Git integration tracks item definitions and metadata, but Lakehouse table and file data are not stored in Git. Workspace-generated logical identifiers and notebook bindings should come from a real workspace rather than being invented in advance.

Official references:

- Medallion architecture in Fabric:
  https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture
- Lakehouse Git integration:
  https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-git-deployment-pipelines
- Notebook source control:
  https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment

## Planned implementation sequence

### PR 2 — Bronze, silver and gold transformations

- import the raw CSV into a Bronze Lakehouse
- preserve source bytes and ingestion metadata
- implement contract validation in a Fabric notebook
- write accepted and rejected silver tables
- publish deterministic quality audit totals
- build initial gold dimensions and fact table

### PR 3 — Semantic model and report

- finalize the star schema
- document relationships and measures
- create operational KPIs
- add a small Power BI report
- capture reproducible screenshots and model evidence

### PR 4 — Fabric lifecycle and portfolio completion

- synchronize real Fabric item definitions
- verify notebook and Lakehouse bindings
- document workspace setup and execution
- add deployment and source-control boundaries
- finalize portfolio presentation

## Acceptance criteria for the first Fabric run

The Fabric implementation must reproduce the local controls:

```text
source rows:  100
valid rows:    89
invalid rows:  11
```

Any difference must be explained before downstream tables or reports are accepted.
