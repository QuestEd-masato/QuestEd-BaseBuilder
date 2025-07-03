-- Ranking System Repair SQL Script
-- ===================================
-- This script repairs the ranking system by calculating rankings with proper user joins

-- 1. Clear old/corrupted data
DELETE FROM ranking_cache WHERE expires_at < NOW();
DELETE FROM rankings WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 2. Check user-answer data integrity
SELECT 
    'User-Answer Data Check' as check_type,
    COUNT(DISTINCT u.id) as users_with_data,
    COUNT(ar.id) as total_answers,
    AVG(ar.is_correct) as avg_accuracy
FROM users u 
JOIN answer_records ar ON u.id = ar.student_id 
WHERE u.role = 'student' AND u.is_active = 1;

-- 3. Generate Total Points Ranking (corrected version)
SELECT 
    ROW_NUMBER() OVER (ORDER BY total_points DESC) as rank_position,
    u.id as student_id,
    u.username as student_name,
    COALESCE(answer_points.points, 0) as total_points,
    COALESCE(answer_counts.total_answers, 0) as total_answers,
    COALESCE(answer_counts.correct_answers, 0) as correct_answers,
    CASE 
        WHEN answer_counts.total_answers > 0 
        THEN ROUND((answer_counts.correct_answers / answer_counts.total_answers) * 100, 1)
        ELSE 0 
    END as accuracy_rate
FROM users u
LEFT JOIN (
    -- Answer points calculation
    SELECT 
        student_id,
        SUM(is_correct * 10) as points  -- 10 points per correct answer
    FROM answer_records 
    GROUP BY student_id
) answer_points ON u.id = answer_points.student_id
LEFT JOIN (
    -- Answer statistics
    SELECT 
        student_id,
        COUNT(*) as total_answers,
        SUM(is_correct) as correct_answers
    FROM answer_records 
    GROUP BY student_id
) answer_counts ON u.id = answer_counts.student_id
WHERE u.role = 'student' 
  AND u.is_active = 1
  AND answer_points.points > 0  -- Only students with learning activity
ORDER BY total_points DESC
LIMIT 20;

-- 4. Generate Accuracy Ranking (minimum 20 answers)
SELECT 
    ROW_NUMBER() OVER (ORDER BY accuracy_rate DESC) as rank_position,
    u.id as student_id,
    u.username as student_name,
    ROUND((SUM(ar.is_correct) / COUNT(ar.id)) * 100, 1) as accuracy_rate,
    COUNT(ar.id) as total_answers,
    SUM(ar.is_correct) as correct_answers
FROM users u
JOIN answer_records ar ON u.id = ar.student_id
WHERE u.role = 'student' 
  AND u.is_active = 1
GROUP BY u.id, u.username
HAVING COUNT(ar.id) >= 20  -- Minimum 20 answers required
ORDER BY accuracy_rate DESC, total_answers DESC
LIMIT 15;

-- 5. Weekly Activity Ranking
SELECT 
    ROW_NUMBER() OVER (ORDER BY weekly_points DESC) as rank_position,
    u.id as student_id,
    u.username as student_name,
    SUM(ar.is_correct * 10) as weekly_points,
    COUNT(ar.id) as weekly_answers,
    COUNT(DISTINCT DATE(ar.created_at)) as active_days
FROM users u
JOIN answer_records ar ON u.id = ar.student_id
WHERE u.role = 'student' 
  AND u.is_active = 1
  AND ar.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY u.id, u.username
HAVING weekly_points > 0
ORDER BY weekly_points DESC, active_days DESC
LIMIT 15;

-- 6. Verify no "Unknown" users in results
SELECT 
    'Data Quality Check' as check_type,
    COUNT(*) as total_active_students,
    SUM(CASE WHEN u.username = 'Unknown' OR u.username IS NULL THEN 1 ELSE 0 END) as unknown_users,
    COUNT(DISTINCT ar.student_id) as students_with_answers
FROM users u
LEFT JOIN answer_records ar ON u.id = ar.student_id
WHERE u.role = 'student' AND u.is_active = 1;