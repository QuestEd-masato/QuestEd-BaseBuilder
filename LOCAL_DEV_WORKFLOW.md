# ローカル開発ワークフロー - QuestEd

## 🔄 開発フロー（GitHub → ローカル → EC2/RDS）

### **Phase 1: ローカル開発・テスト**
```bash
# 1. 最新のコード取得
git pull origin main

# 2. 仮想環境有効化
source venv/bin/activate

# 3. ローカルサーバー起動
python run.py
# → http://localhost:5000 でテスト

# 4. ローカルDB接続確認
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested
```

### **Phase 2: テストとデバッグ**
```bash
# 5. 修正・テスト実行
# 修正ファイルの動作確認
# データベースマイグレーション（必要に応じて）

# 6. ローカルテスト
# http://localhost:5000/student/learning
# http://localhost:5000/teacher/curriculum/14/edit
```

### **Phase 3: GitHub経由のデプロイ**
```bash
# 7. 変更をコミット
git add .
git commit -m "Fix lesson list error and curriculum save issues

🎯 Problems solved:
- Add missing student_task_progress table
- Fix ActivityLog model inconsistency  
- Improve curriculum save data flow

📊 Technical details:
- Create student_task_progress table with proper schema
- Add activity_type column to ActivityLog
- Enhance error handling in curriculum save process

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 8. GitHubにプッシュ
git push origin main
```

### **Phase 4: EC2/RDS同期**
```bash
# 9. EC2で最新コード取得
ssh -i ~/.ssh/quested-key.pem ec2-user@13.113.164.85 \
  "cd /var/www/quested/QuestEd && git pull"

# 10. DBマイグレーション実行（必要に応じて）
ssh -i ~/.ssh/quested-key.pem ec2-user@13.113.164.85 \
  "cd /var/www/quested/QuestEd && source venv/bin/activate && python migrate_script.py"

# 11. サービス再起動
ssh -i ~/.ssh/quested-key.pem ec2-user@13.113.164.85 \
  "sudo systemctl restart quested"

# 12. 本番動作確認
# https://quest-ed.jp/student/learning
# https://quest-ed.jp/teacher/curriculum/14/edit
```

## 🗂️ データベース接続情報

### **ローカル開発DB**
```bash
Host: localhost
Port: 3306
Database: quested
Username: QuestEd
Password: QuestEd-03012025MySQL

# 接続コマンド
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested
```

### **本番RDS（EC2経由）**
```bash
# EC2経由でのRDS接続
ssh -i ~/.ssh/quested-key.pem ec2-user@13.113.164.85

# EC2内からRDS接続
mysql -u root -p'masato1873_QuestEd-03012025' \
  -h database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com \
  quested
```

## 📊 マイグレーション管理

### **ローカルでマイグレーションファイル作成**
```bash
# Flask-Migrateを使用（推奨）
source venv/bin/activate
export FLASK_APP=run.py
flask db migrate -m "Add student_task_progress table and fix ActivityLog"
flask db upgrade

# 手動SQLファイル作成（代替案）
cat > migrations/manual_sql/fix_lesson_tables_$(date +%Y%m%d).sql << 'EOF'
-- Fix for lesson system tables
-- Date: $(date +%Y-%m-%d)

-- Add missing student_task_progress table
CREATE TABLE student_task_progress (
  id INT PRIMARY KEY AUTO_INCREMENT,
  student_id INT NOT NULL,
  task_id INT NOT NULL,
  status ENUM('NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'COMPLETED') DEFAULT 'NOT_STARTED',
  progress_percentage DECIMAL(5,2) DEFAULT 0.00,
  started_at DATETIME NULL,
  submitted_at DATETIME NULL,
  completed_at DATETIME NULL,
  last_activity_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES users(id),
  FOREIGN KEY (task_id) REFERENCES lesson_tasks(id)
);

-- Add activity_type to ActivityLog if missing
ALTER TABLE activity_logs 
ADD COLUMN activity_type VARCHAR(50) DEFAULT 'general';
EOF
```

### **EC2/RDSでマイグレーション実行**
```bash
# EC2にマイグレーションファイル同期
scp -i ~/.ssh/quested-key.pem \
  migrations/manual_sql/fix_lesson_tables_*.sql \
  ec2-user@13.113.164.85:/tmp/

# EC2でマイグレーション実行
ssh -i ~/.ssh/quested-key.pem ec2-user@13.113.164.85 \
  "mysql -u root -p'masato1873_QuestEd-03012025' \
   -h database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com \
   quested < /tmp/fix_lesson_tables_*.sql"
```

## ⚠️ 注意事項

1. **データベース同期**: ローカルとRDSが同期されているため、テーブル作成はローカルで検証後にRDSに適用
2. **バックアップ必須**: 本番DB変更前は必ずバックアップ
3. **段階的デプロイ**: ローカル → ステージング → 本番の順序を守る
4. **ロールバック準備**: 問題発生時の復旧手順を事前準備