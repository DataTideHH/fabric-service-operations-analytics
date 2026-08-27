# Governed AI handoff contract

The AI handoff converts the existing reconciled analytics evidence into one small, versioned JSON snapshot for `service-operations-ai-orchestration`. It is a build-time handoff, not a live dependency between repositories.

## Inputs

- `evidence/analytics_manifest.json`
- `evidence/sla_by_team.csv`
- `analytics/metric_contract.json`
- the full Git revision that owns those inputs
- the bounded synthetic reporting period

The exporter verifies that global eligible, within-SLA and breached counts reconcile to the team totals. It derives percentages from integer counts, orders teams by observed breach rate and fingerprints every source input.

## Output

`evidence/ai_service_operations_snapshot.json` conforms to `contracts/ai-service-operations-snapshot.schema.json`. The snapshot identifies its producer, source repository and revision, ingestion batch, reporting period, metric denominator, comparison dimension and interpretation boundary.

The downstream repository commits an exact copy so builds remain deterministic and do not require a network connection. A changed source fingerprint, contract or evidence value is a deliberate versioned update.

## Boundaries

The handoff contains a deterministic synthetic scenario, not production observations. It supports descriptive SLA interpretation and comparisons by assigned team. It does not support causal explanations, forecasts or judgments about team quality.
