# Local Medallion Pipeline

## Purpose

This pipeline implements the transformation and reconciliation contract locally before the same logic is transferred to Microsoft Fabric. The approach follows the Bronze, Silver and Gold quality progression recommended for Fabric Lakehouse solutions.

Official Microsoft reference:

- https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture

## Command

```bash
python -m service_operations build-medallion \
  --input data/raw/service_requests.csv \
  --contract contracts/service_requests.contract.json \
  --output .ci-output/medallion
```

## Reconciliation rules

A run is accepted only when all controls are true:

```text
Bronze rows = Silver valid rows + Silver rejected rows
Silver valid rows = Gold fact rows
Every Gold fact foreign key resolves to its dimension
Generated manifest = committed manifest evidence
Generated KPI table = committed KPI evidence
```

For the committed fixture:

```text
Bronze:          100
Silver valid:     89
Silver rejected:  11
Gold fact:        89
```

## Rejection handling

Silver rejection output preserves the complete source-shaped record and adds:

- `rejection_reasons`: sorted, pipe-separated issue codes
- `issue_count`: number of issue records attached to the source row

The separate issue-level Parquet table retains one row per validation issue for audit and later comparison with a Fabric data-quality table.

## Gold model grain

`fact_service_requests` has one row per accepted service request. It contains foreign keys to:

- `dim_date` through created and closed date keys
- `dim_team`
- `dim_category`
- `dim_priority`

Ticket ID remains a degenerate business identifier. Customer segment and source system remain low-cardinality fact attributes for this bounded model.

## Why generated Parquet is not committed

The Parquet layers are deterministic in content but are build outputs rather than source files. They are generated locally and in GitHub Actions, tested by reading them back and uploaded as short-lived CI artefacts. Git stores only the readable source, transformation logic, tests and reconciled text evidence.
