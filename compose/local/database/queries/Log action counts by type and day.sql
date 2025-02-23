SELECT 
	COUNT(*) AS action_count,
    action_type,
    result,
    DATE(created_at) AS action_date
    FROM logs
GROUP BY action_date, action_type, result
ORDER BY action_date DESC, action_type, result;
