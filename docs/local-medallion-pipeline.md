# Local Medallion Pipeline

## Purpose

This pipeline implements the transformation and reconciliation contract locally before the same logic is transferred to Microsoft Fabric. The approach follows a Bronze, Silver and Gold quality progression.

Official Microsoft reference:

- https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture

## Commands

Generate the deterministic 1,000-row synthetic source:

```bash
python -m service_operations generate \
  --output .ci-output/service_requests.csv
```

Build the local Medallion layers:

```bash
python -m service_operations build-medallion \
  --input .ci-output/service_requests.csv \
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

For the generated fixture:

```text
Bronze:          1,000
Silver valid:      989
Silver rejected:    11
Gold fact:          989
```

## Operational KPI semantics

```text
SLA compliance = SLA-met closed tickets / SLA-eligible closed tickets
Reopen rate     = closed tickets reopened at least once / closed tickets
Escalation rate = escalated accepted tickets / accepted tickets
Backlog rate    = open accepted tickets / accepted tickets
```

The generator is tested against these bounded scenario-design ranges:

```text
SLA compliance: 93–96%
Reopen rate:      5–9%
Escalation rate:  7–12%
Open backlog:    10–18%
```

These ranges describe the synthetic portfolio scenario. They are not presented as universal service-management benchmarks.

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

## Why generated source and Parquet are not committed

The source CSV and Parquet layers are deterministic derived outputs. Git stores the readable generator, data contract, transformation logic, tests and reconciled text evidence. Tests and GitHub Actions verify the generated CSV fingerprint, read the Parquet outputs back and upload short-lived build artefacts.
