SELECT 
    action_type, 
    COUNT(*) AS action_count
FROM logs
WHERE result = 'success'
AND DATE(created_at) = CURDATE()
GROUP BY action_type
ORDER BY action_count DESC;
