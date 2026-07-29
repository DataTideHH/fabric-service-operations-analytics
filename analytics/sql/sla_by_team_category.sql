SELECT
    assigned_team,
    category,
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
    ) AS sla_breach_rate
FROM service_requests_enriched
WHERE status = 'closed'
GROUP BY assigned_team, category
ORDER BY assigned_team, category
