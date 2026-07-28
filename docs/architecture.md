# Architecture Baseline

## Current PR 1 scope

The current implementation is intentionally local and platform-neutral:

```text
deterministic generator
        |
        v
synthetic raw CSV
        |
        v
machine-readable data contract
        |
        v
row-level validation
        |
        +--> validation report
        |
        +--> automated local and CI tests
```

This proves that the source fixture, contract and quality expectations are reproducible before any cloud resources are created.

## Planned Microsoft Fabric mapping

```text
Repository baseline                 Planned Fabric item
-----------------------------------------------------------------------
data/raw/service_requests.csv       Bronze Lakehouse Files area
contract validation                 Silver transformation notebook
accepted typed records              Silver Delta table
service-operation dimensions        Gold dimension tables
service-operation facts             Gold fact table
quality control totals              Data-quality audit table
orchestration specification         Data Factory pipeline
curated model                       Power BI semantic model / Direct Lake
```

The planned target follows a bronze, silver and gold medallion structure:

- **Bronze:** retain source-shaped data and ingestion metadata.
- **Silver:** apply typing, contract checks, deduplication and rejection logic.
- **Gold:** publish a small star schema and operational KPIs.

## Explicit non-claims

PR 1 does not claim:

- execution in a Fabric workspace
- creation of a Lakehouse or OneLake objects
- execution with Fabric Spark
- a working Data Factory pipeline
- a SQL analytics endpoint
- a Direct Lake semantic model
- a deployed Power BI report
- Fabric Git synchronization

Fabric-generated definitions and workspace identifiers will only be committed after they are exported or synchronized from a real workspace.
