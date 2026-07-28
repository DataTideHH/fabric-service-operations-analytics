# Data-Quality Rules

The fixture contains 100 rows and a bounded set of intentional defects.

Expected controls:

```text
total rows:   100
valid rows:    89
invalid rows:  11
valid rate:  89.0%
```

## Expected issue counts

| Issue code | Count |
|---|---:|
| `closed_before_created` | 1 |
| `closed_missing_closed_at` | 1 |
| `duplicate_ticket_id` | 2 |
| `invalid_assigned_team` | 1 |
| `invalid_escalated` | 1 |
| `invalid_priority` | 1 |
| `missing_required_value` | 1 |
| `negative_resolution_minutes` | 1 |
| `open_has_closed_at` | 1 |
| `sla_priority_mismatch` | 1 |

The duplicate identifier affects two rows, so both rows are invalid.

## Validation principles

- Raw fields are loaded as text before controlled conversion.
- Missing required values are reported explicitly.
- Domain checks avoid silently coercing unknown categories.
- Invalid identifiers are retained as evidence rather than corrected.
- All duplicate primary-key occurrences are rejected.
- Business-rule checks are separated from type checks.
- The validation report is deterministic and machine-readable.
- CI compares a freshly generated fixture byte-for-byte with the committed CSV.
