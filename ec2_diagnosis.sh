#!/bin/bash
echo "=== QuestEd EC2 診断スクリプト ==="
echo "実行日時: $(date)"
echo ""

echo "1. Git状態確認"
echo "現在のブランチ: $(git branch --show-current)"
echo "最新コミット: $(git log --oneline -1)"
echo "ワーキングディレクトリの状態:"
git status --porcelain
echo ""

echo "2. ファイル存在確認"
echo "problem_session.html: $(ls -la templates/basebuilder/problem_session.html 2>/dev/null || echo 'NOT FOUND')"
echo "categories_student.html: $(ls -la templates/basebuilder/categories_student.html 2>/dev/null || echo 'NOT FOUND')"
echo "categories_simple.html: $(ls -la templates/basebuilder/categories_simple.html 2>/dev/null || echo 'NOT FOUND')"
echo ""

echo "3. Python構文チェック"
python3 -m py_compile basebuilder/routes_modules/sessions.py && echo "sessions.py: OK" || echo "sessions.py: SYNTAX ERROR"
python3 -m py_compile basebuilder/routes_modules/categories.py && echo "categories.py: OK" || echo "categories.py: SYNTAX ERROR"
echo ""

echo "4. データベース接続テスト"
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "SELECT 'DB Connection: OK'" 2>/dev/null || echo "DB Connection: FAILED"
echo ""

echo "5. DB3300カテゴリ確認"
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "
SELECT c.id, c.name, 
       COUNT(b.id) as total_problems,
       SUM(CASE WHEN b.is_active = 1 THEN 1 ELSE 0 END) as active_problems
FROM problem_categories c 
LEFT JOIN basic_knowledge_items b ON c.id = b.category_id 
WHERE c.name LIKE '%DB3300%' 
GROUP BY c.id, c.name;" 2>/dev/null || echo "DB3300 query failed"
echo ""

echo "6. 教師アカウント確認"
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested -e "
SELECT id, username, email, role, is_approved, is_active 
FROM users 
WHERE role = 'teacher' 
LIMIT 5;" 2>/dev/null || echo "Teacher query failed"
echo ""

echo "7. プロセス確認"
echo "Python processes:"
ps aux | grep python | grep -v grep || echo "No Python processes found"
echo ""

echo "8. ポート確認"
echo "Port 5000 status:"
netstat -tlnp | grep :5000 || echo "Port 5000 not listening"
echo ""

echo "9. アプリケーションログ確認"
if [ -f "app.log" ]; then
    echo "Recent log entries:"
    tail -20 app.log | grep -E "(ERROR|Exception|SUCCESS|INFO)"
else
    echo "app.log not found"
fi
echo ""

echo "=== 診断完了 ==="