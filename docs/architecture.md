# Architecture

## Implemented local pipeline

The local implementation follows the same quality progression intended for the later Microsoft Fabric Lakehouse:

```text
deterministic generator
        |
        v
synthetic raw CSV
        |
        v
Bronze: source-shaped Parquet + ingestion metadata
        |
        v
machine-readable contract validation
        |
        +------------------------------+
        |                              |
        v                              v
Silver valid: typed Parquet       Silver rejected: raw values
                                  + rejection reasons
        |                              |
        |                              +--> issue-level audit table
        v
Gold star schema
fact_service_requests
+ dim_date
+ dim_team
+ dim_category
+ dim_priority
        |
        v
service_operations_kpis.csv
+ medallion_manifest.json
```

The implementation proves that the raw fixture, data-quality rules, accepted and rejected populations, foreign keys and KPI calculations reconcile before a cloud workspace exists.

## Layer responsibilities

### Bronze

- preserves all 100 source rows
- keeps source values as text
- records the original CSV line number
- records the source file
- derives a deterministic ingestion batch identifier from the source bytes
- adds a fixed portfolio-fixture ingestion timestamp

### Silver

- applies the existing machine-readable data contract
- produces 89 typed valid records
- produces 11 rejected source records
- retains pipe-separated rejection reasons on each rejected row
- retains 11 issue-level audit records
- converts timestamps, integer fields and booleans to explicit types
- derives a nullable `sla_met` field for closed requests

### Gold

- publishes an 89-row fact table
- publishes date, team, category and priority dimensions
- verifies every fact foreign key
- calculates reconciled SLA, backlog, resolution, escalation and reopening KPIs
- writes a stable JSON manifest for automated comparison

## Planned Microsoft Fabric mapping

```text
Local implementation                         Planned Fabric item
----------------------------------------------------------------------------
data/raw/service_requests.csv                 Bronze Lakehouse Files area
bronze/service_requests.parquet               Bronze table or Files output
contract validation                           Fabric notebook transformation
silver/service_requests_valid.parquet         Silver Delta table
silver/service_requests_rejected.parquet      Silver rejection table
silver/service_request_issues.parquet         Data-quality audit table
gold/dim_*.parquet                            Gold dimension tables
gold/fact_service_requests.parquet            Gold fact table
gold/service_operations_kpis.csv              KPI validation table
medallion_manifest.json                       Pipeline control evidence
curated Gold model                            Direct Lake semantic model
```

## Explicit non-claims

The repository still does not claim:

- execution in a Fabric workspace
- creation of Lakehouse or OneLake objects
- Fabric Spark or notebook execution
- a working Data Factory pipeline
- a SQL analytics endpoint
- a Direct Lake semantic model
- a deployed Power BI report
- Fabric Git synchronization

Fabric-generated definitions and workspace identifiers will only be committed after they are exported or synchronized from a real workspace.
