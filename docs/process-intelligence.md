# Process Intelligence Layer

## Purpose

The process-intelligence layer converts the validated 989-row Silver service-request population into a deterministic, process-mining-ready event log and a set of reviewable process-analysis outputs.

It addresses four bounded questions:

1. Which process variants occur in the synthetic operating scenario?
2. Which transitions contain the largest derived waiting-time concentrations?
3. How do escalation and reopening paths differ from the standard path?
4. Can all process outputs reconcile to the existing Silver population and source fields?

## Interpretation boundary

The source model stores ticket creation, final closure, escalation status and reopening count. It does not store observed status-history rows or production event timestamps.

Intermediate event timestamps are therefore deterministic scenario derivations between ticket creation and final closure. The event log is suitable for learning, testing and later Process Mining integration design. It is not represented as observed production history and does not support causal root-cause claims.

Every event row contains:

- `case_id`
- `event_id`
- `event_index`
- `activity`
- `event_timestamp`
- team, category, priority and customer-segment context
- final case status
- SLA, escalation and reopening context
- `event_origin = derived_synthetic_scenario`

## Activity model

All valid cases begin with:

```text
ticket_created > team_assigned
```

Closed standard cases continue with:

```text
resolution_recorded > ticket_closed
```

Escalated cases add `escalated`. Reopened cases add one or two deterministic `resolution_recorded > reopened` cycles before final resolution and closure. Open cases have no closure event.

## Implemented outputs

| Output | Purpose |
|---|---|
| `event_log` | case/activity/timestamp event table for process-mining tools |
| `process_cases` | one row per case with variant, observed span, throughput and exception type |
| `process_variants` | variant frequency, share, throughput and SLA-breach context |
| `transition_performance` | transition counts and average, median and p90 wait |
| `bottlenecks` | ranked waiting-time concentrations with an explicit non-causal boundary |
| `exception_paths` | escalated-only, reopened-only and combined paths |
| `process_intelligence_manifest` | row counts, case populations and reconciliation controls |

CSV and Parquet versions are written for the event log and case table. Summary outputs are also written as CSV for direct review.

## Verified baseline

```text
valid cases:          989
event rows:         3,831
closed cases:         833
open cases:           156
escalated cases:       85
reopened cases:        48
reopen occurrences:    51
process variants:       7
transitions:            7
exception path types:   3
```

The leading standard variant contains 714 cases. The largest derived waiting-time concentration is `team_assigned > resolution_recorded`, covering 758 transitions with an average derived wait of 712.59 minutes.

These figures describe the committed synthetic scenario only. They are not industry benchmarks.

## Reconciliation controls

The build fails unless:

- case count equals the validated Silver population
- event identifiers are unique
- event indexes are contiguous within each case
- timestamps are monotonic within each case
- every case starts with `ticket_created`
- every closed case ends with `ticket_closed`
- open cases do not end with `ticket_closed`
- reopened-event count equals the source reopening total
- escalation-event count equals the source escalation total
- closed-case throughput equals the source resolution duration

## Command

```bash
python -m service_operations build-process-intelligence \
  --input .ci-output/service_requests.csv \
  --contract contracts/service_requests.contract.json \
  --output .ci-output/process-intelligence
```

## Later Process Mining mapping

The local event log already uses the core columns expected by most Process Mining tools: case identifier, activity and timestamp. A later Fabric or Power Platform implementation may map it to:

- Fabric Lakehouse or Warehouse event tables
- Power BI process-analysis reporting
- Power Automate Process Mining or another Process Mining engine
- object-centric event models after real assignment, status, change and supplier objects exist

Object-centric Process Mining is not claimed in the current source model because only the service-request case object is represented.
