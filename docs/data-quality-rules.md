# Data-Quality Rules

The deterministic generator creates 1,000 source rows and applies a bounded set of ten intentional anomaly mutations. One mutation duplicates a clean identifier, so both duplicate occurrences are rejected and the final invalid-row count is eleven.

Expected controls:

```text
total rows:    1,000
valid rows:      989
invalid rows:     11
valid rate:     98.9%
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
- CI generates the source on both operating systems and verifies its complete SHA-256 fingerprint before validation.
