# SLA Breach Analysis

This evidence is generated from the local Gold Parquet tables through the versioned DuckDB SQL layer in [`analytics/sql/`](../analytics/sql/). It describes the bounded synthetic 90-day scenario and is not a production benchmark.

## Reconciled population

| Measure | Value |
|---|---:|
| Accepted requests | 989 |
| Closed and SLA-eligible requests | 833 |
| SLA-met requests | 799 |
| SLA breaches | 34 |
| SLA compliance | 95.92% |

The breach population reconciles exactly:

```text
799 SLA-met + 34 SLA-breached = 833 closed and SLA-eligible requests
```

## Concentration by team

| Team | Closed | Breaches | Breach rate |
|---|---:|---:|---:|
| business_apps | 209 | 10 | 4.78% |
| data_platform | 114 | 7 | 6.14% |
| network_ops | 129 | 9 | 6.98% |
| service_desk | 234 | 7 | 2.99% |
| workplace | 147 | 1 | 0.68% |

`business_apps` has the highest breach count, while `network_ops` has the highest team-level breach rate. This distinction matters because counts and rates answer different operational questions.

## Concentration by category

| Category | Closed | Breaches | Breach rate |
|---|---:|---:|---:|
| access | 211 | 3 | 1.42% |
| application | 230 | 16 | 6.96% |
| hardware | 134 | 1 | 0.75% |
| network | 140 | 12 | 8.57% |
| reporting | 118 | 2 | 1.69% |

Application requests contribute the largest breach count. Network requests have the highest category-level breach rate.

## Concentration by priority

| Priority | Closed | Breaches | Breach rate |
|---|---:|---:|---:|
| P1 | 22 | 4 | 18.18% |
| P2 | 157 | 9 | 5.73% |
| P3 | 449 | 17 | 3.79% |
| P4 | 205 | 4 | 1.95% |

P1 has the highest breach rate but a small denominator. P3 contributes the largest absolute number of breaches because it contains the largest closed-ticket population.

## Interpretation boundary

The analysis identifies concentration and association patterns. It does not establish root cause. The source model does not contain cause codes, waiting-state history, assignment changes, supplier dependencies, linked changes or linked problem records. A later operational source would need those fields before causal conclusions could be supported.
