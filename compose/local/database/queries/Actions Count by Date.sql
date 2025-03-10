SELECT 
    DATE(created_at) AS action_date, 
    COUNT(*) AS action_count
FROM logs
WHERE result = 'success'
GROUP BY action_date
ORDER BY action_date DESC;
