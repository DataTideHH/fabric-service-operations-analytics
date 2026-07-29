SELECT
    fact.ticket_id,
    CAST(created_date.full_date AS DATE) AS created_date,
    CAST(closed_date.full_date AS DATE) AS closed_date,
    team.assigned_team,
    category.category,
    priority.priority,
    fact.status,
    fact.sla_target_minutes,
    fact.resolution_minutes,
    fact.reopened_count,
    fact.escalated,
    fact.sla_met,
    CASE
        WHEN fact.status = 'closed' AND fact.sla_met = FALSE THEN TRUE
        ELSE FALSE
    END AS sla_breached,
    CASE
        WHEN fact.status = 'closed' THEN ROUND(
            CAST(fact.resolution_minutes AS DOUBLE)
            / NULLIF(CAST(fact.sla_target_minutes AS DOUBLE), 0),
            4
        )
        ELSE NULL
    END AS resolution_ratio,
    CASE
        WHEN fact.status = 'closed' AND fact.sla_met = FALSE
            THEN fact.resolution_minutes - fact.sla_target_minutes
        ELSE 0
    END AS resolution_overrun_minutes,
    fact.customer_segment,
    fact.source_system,
    fact.source_row,
    fact.ingestion_batch_id
FROM fact_service_requests AS fact
JOIN dim_date AS created_date
    ON fact.created_date_key = created_date.date_key
LEFT JOIN dim_date AS closed_date
    ON fact.closed_date_key = closed_date.date_key
JOIN dim_team AS team
    ON fact.team_key = team.team_key
JOIN dim_category AS category
    ON fact.category_key = category.category_key
JOIN dim_priority AS priority
    ON fact.priority_key = priority.priority_key
