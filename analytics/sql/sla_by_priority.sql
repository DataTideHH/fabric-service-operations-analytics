SELECT
    priority,
    COUNT(*)::BIGINT AS closed_requests,
    SUM(CASE WHEN sla_met = TRUE THEN 1 ELSE 0 END)::BIGINT AS sla_met_requests,
    SUM(CASE WHEN sla_breached = TRUE THEN 1 ELSE 0 END)::BIGINT AS sla_breaches,
    ROUND(
        SUM(CASE WHEN sla_met = TRUE THEN 1 ELSE 0 END)::DOUBLE / COUNT(*),
        4
    ) AS sla_compliance_rate,
    ROUND(
        SUM(CASE WHEN sla_breached = TRUE THEN 1 ELSE 0 END)::DOUBLE / COUNT(*),
        4
    ) AS sla_breach_rate,
    SUM(CASE WHEN escalated = TRUE THEN 1 ELSE 0 END)::BIGINT AS escalated_closed_requests,
    ROUND(
        SUM(CASE WHEN escalated = TRUE THEN 1 ELSE 0 END)::DOUBLE / COUNT(*),
        4
    ) AS closed_escalation_rate,
    SUM(CASE WHEN reopened_count > 0 THEN 1 ELSE 0 END)::BIGINT AS reopened_requests,
    ROUND(
        SUM(CASE WHEN reopened_count > 0 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*),
        4
    ) AS reopen_rate,
    ROUND(AVG(resolution_minutes::DOUBLE), 2) AS average_resolution_minutes,
    ROUND(MEDIAN(resolution_minutes::DOUBLE), 2) AS median_resolution_minutes
FROM service_requests_enriched
WHERE status = 'closed'
GROUP BY priority
ORDER BY priority
