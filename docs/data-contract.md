# Service-Request Data Contract

The source of truth is [`contracts/service_requests.contract.json`](../contracts/service_requests.contract.json).

## Scenario and grain

The contract describes a deterministic synthetic 90-day sample for one customer environment and five operational teams. The generator creates 1,000 source rows; one row represents one service request at its current lifecycle state.

The documented KPI ranges are constraints for this synthetic portfolio scenario, not universal service-management benchmarks.

## Primary key

`ticket_id`

All occurrences of a duplicated identifier are rejected. The validator does not guess which record should survive.

## Columns

| Column | Meaning | Rule |
|---|---|---|
| `ticket_id` | Synthetic request identifier | Required, unique, `SR-######` |
| `created_at` | UTC creation timestamp | Required ISO-style UTC value |
| `closed_at` | UTC closure timestamp | Required only for closed requests |
| `priority` | Operational priority | `P1` to `P4` |
| `category` | Request category | Controlled domain |
| `assigned_team` | Current resolver team | Controlled domain |
| `status` | Lifecycle state | `open` or `closed` |
| `sla_target_minutes` | Resolution target | Must match priority mapping |
| `resolution_minutes` | Resolution duration | Non-negative; closed requests only |
| `reopened_count` | Number of reopenings | Integer from 0 to 5; zero for open requests |
| `escalated` | Escalation marker | `true` or `false` |
| `customer_segment` | Synthetic reporting segment | Controlled domain |
| `source_system` | Source identifier | `service_portal` |

## SLA mapping

| Priority | Target minutes |
|---|---:|
| P1 | 240 |
| P2 | 480 |
| P3 | 1,440 |
| P4 | 2,880 |

## KPI eligibility

- SLA compliance uses closed, SLA-eligible tickets.
- Reopen rate uses closed tickets because open tickets cannot yet be reopened.
- Escalation rate and backlog rate use all accepted tickets.

## Privacy and safety

The fixture is synthetic and contains no names, email addresses, phone numbers, postal addresses or free-text incident descriptions. This keeps the repository public-safe and prevents accidental inclusion of operational or personal data.
