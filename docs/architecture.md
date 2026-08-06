# Architecture

## Implemented local pipeline

The local implementation follows the quality progression intended for a later Microsoft Fabric Lakehouse, adds a transparent SQL analytics layer and now derives a controlled process-intelligence layer before any BI-specific artefact is claimed:

```text
deterministic generator
        |
        v
generated synthetic CSV
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
        |
        +------------------------------+
        |                              |
        v                              v
Gold star schema                 derived process event log
fact_service_requests            + case summaries
+ dim_date                       + process variants
+ dim_team                       + transition performance
+ dim_category                   + bottleneck ranking
+ dim_priority                   + exception paths
        |                              |
        v                              v
Gold KPI evidence                process-intelligence manifest
        |
        v
DuckDB SQL analytics layer
+ enriched request view
+ SLA marts by team, category and priority
+ team-category matrix
+ daily operations mart
+ SLA breach detail mart
        |
        v
analytics manifest + reviewable CSV/Markdown evidence
```

The implementation proves that generated source bytes, data-quality rules, accepted and rejected populations, Gold foreign keys, KPI calculations, grouped analytical results and derived process outputs reconcile before a cloud workspace or Power BI report exists.

## Synthetic operating scenario

The generator models one customer environment over a 90-day analysis window with five operational teams. Category, priority and team assignment are correlated rather than independently randomized. SLA breaches influence escalation probability, and reopenings can occur only after a ticket has been closed.

The documented KPI ranges are design constraints for this synthetic scenario, not claimed industry benchmarks:

| KPI | Design range |
|---|---:|
| SLA compliance | 93–96% |
| Reopen rate | 5–9% |
| Escalation rate | 7–12% |
| Open backlog rate | 10–18% |

## Layer responsibilities

### Generated source

- creates 1,000 deterministic source rows from seed `20260729`
- distributes creation timestamps across 90 days
- models category-to-team and category-to-priority relationships
- injects ten bounded anomaly mutations that cause eleven rejected rows
- produces a stable SHA-256 fingerprint verified in tests and CI
- is generated on demand rather than committed as a large derived CSV

### Bronze

- preserves all 1,000 source rows
- keeps source values as text
- records original line, source file, batch identifier and ingestion timestamp

### Silver

- applies the machine-readable data contract
- produces 989 typed valid records and 11 rejected records
- retains rejection and issue-level audit evidence
- converts timestamps, integers and booleans to explicit types
- derives nullable SLA eligibility and outcome

### Gold

- publishes a 989-row fact table plus date, team, category and priority dimensions
- verifies every fact foreign key
- calculates reconciled SLA, backlog, resolution, escalation and reopening KPIs
- writes a stable JSON manifest for automated comparison

### SQL analytics

- reads Gold Parquet directly with DuckDB
- keeps analytical logic in versioned SQL
- publishes an enriched request mart, grouped SLA marts, daily operations and 34 breach details
- distinguishes count from rate and reconciles every grouped population
- identifies concentration and association patterns without claiming causal root cause

### Process intelligence

- derives 3,831 ordered events over the 989 validated cases
- provides case, activity and timestamp columns suitable for later Process Mining tools
- publishes seven process variants and seven transition types
- ranks waiting-time concentrations with an explicit non-causal interpretation boundary
- compares escalated-only, reopened-only and combined exception paths
- reconciles event counts to source escalation and reopening fields
- marks every event as `derived_synthetic_scenario`

The source does not contain observed status-history timestamps. Intermediate process events are deterministic scenario derivations, not production telemetry.

## Planned Microsoft Fabric mapping

```text
Local implementation                         Planned Fabric item
----------------------------------------------------------------------------
generated service_requests.csv                Bronze Lakehouse Files area
bronze/service_requests.parquet               Bronze table or Files output
contract validation                           Fabric notebook transformation
silver/service_requests_valid.parquet         Silver Delta table
silver rejection and issue Parquet            Data-quality audit tables
gold/dim_*.parquet                            Gold dimension tables
gold/fact_service_requests.parquet            Gold fact table
gold/service_operations_kpis.csv              KPI validation table
DuckDB SQL marts                              Warehouse/Lakehouse SQL views or tables
process event log                             Lakehouse/Warehouse process event table
process summary outputs                       Process Mining or Power BI model inputs
curated Gold model                            Direct Lake semantic model
```

## Explicit non-claims

The repository still does not claim:

- execution in a Fabric workspace
- creation of Lakehouse or OneLake objects
- Fabric Spark or notebook execution
- a working Data Factory pipeline
- a Fabric SQL analytics endpoint
- a Direct Lake semantic model
- a deployed Power BI report
- Fabric Git synchronization
- observed production event history
- object-centric Process Mining
- causal process root-cause analysis

Fabric-generated definitions and workspace identifiers will only be committed after they are exported or synchronized from a real workspace.
