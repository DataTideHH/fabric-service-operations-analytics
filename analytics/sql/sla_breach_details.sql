SELECT
    ticket_id,
    created_date,
    closed_date,
    assigned_team,
    category,
    priority,
    customer_segment,
    status,
    sla_target_minutes,
    resolution_minutes,
    resolution_overrun_minutes,
    resolution_ratio,
    reopened_count,
    escalated,
    ingestion_batch_id
FROM service_requests_enriched
WHERE sla_breached = TRUE
ORDER BY resolution_overrun_minutes DESC, ticket_id
