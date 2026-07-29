SELECT
    created_date,
    COUNT(*)::BIGINT AS total_requests,
    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END)::BIGINT AS closed_requests,
    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END)::BIGINT AS open_requests,
    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END)::BIGINT AS sla_eligible_requests,
    SUM(CASE WHEN sla_met = TRUE THEN 1 ELSE 0 END)::BIGINT AS sla_met_requests,
    SUM(CASE WHEN sla_breached = TRUE THEN 1 ELSE 0 END)::BIGINT AS sla_breaches,
    ROUND(
        SUM(CASE WHEN sla_met = TRUE THEN 1 ELSE 0 END)::DOUBLE
        / NULLIF(SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END), 0),
        4
    ) AS sla_compliance_rate,
    ROUND(
        SUM(CASE WHEN sla_breached = TRUE THEN 1 ELSE 0 END)::DOUBLE
        / NULLIF(SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END), 0),
        4
    ) AS sla_breach_rate,
    SUM(CASE WHEN escalated = TRUE THEN 1 ELSE 0 END)::BIGINT AS escalated_requests,
    SUM(CASE WHEN reopened_count > 0 THEN 1 ELSE 0 END)::BIGINT AS reopened_requests
FROM service_requests_enriched
GROUP BY created_date
ORDER BY created_date
