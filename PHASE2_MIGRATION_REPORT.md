# Phase2 マイグレーション詳細レポート

## 概要
Phase2では、自由進度学習システムに承認ワークフロー機能を追加し、既存のデータ不整合を修正します。

## 1. データベーススキーマ変更

### 1.1 StudentUnitSelectionテーブルへの新規カラム追加

#### 追加カラム一覧
| カラム名 | データ型 | デフォルト値 | 説明 |
|---------|---------|------------|------|
| approval_status | ENUM('none', 'pending', 'approved', 'rejected') | 'none' | 承認状況 |
| completion_request_date | DATETIME | NULL | 完了申請日時 |
| teacher_comments | TEXT | NULL | 教師コメント |
| approved_by | INT | NULL | 承認者ID（外部キー: users.id） |
| approved_at | DATETIME | NULL | 承認日時 |
| rejection_reason | TEXT | NULL | 却下理由 |

#### 新規インデックス
- `idx_approval_status`: 承認状況での検索最適化
- `idx_completion_request_date`: 申請日時順のソート用
- `idx_approved_by`: 承認者別の検索用
- `idx_approval_workflow`: 複合インデックス（class_id, approval_status, completion_request_date）
- `idx_teacher_pending_approvals`: 部分インデックス（approval_status = 'pending'の行のみ）

### 1.2 ClassLearningSettingsテーブルへの新規カラム追加

#### 追加カラム一覧
| カラム名 | データ型 | デフォルト値 | 説明 |
|---------|---------|------------|------|
| require_teacher_approval | BOOLEAN | TRUE | 教師承認必須フラグ |
| auto_approve_threshold | DECIMAL(5,2) | 90.00 | 自動承認閾値（%） |
| approval_comment_required | BOOLEAN | TRUE | 承認時コメント必須フラグ |
| allow_resubmission | BOOLEAN | TRUE | 再申請許可フラグ |

## 2. 既存データへの影響

### 2.1 デフォルト値による影響
- **既存の student_unit_selections レコード**
  - `approval_status` = 'none'（未申請）として扱われる
  - 完了済み（status='completed'）かつ進捗率80%以上のレコードは自動的に'approved'に更新可能

- **既存の class_learning_settings レコード**
  - デフォルトで教師承認が必須（`require_teacher_approval` = TRUE）
  - 90%以上の進捗で自動承認（`auto_approve_threshold` = 90.00）

### 2.2 外部キー制約
- `approved_by` → `users.id`への外部キー制約追加
- ON DELETE SET NULL設定により、承認者が削除されてもデータは保持

## 3. Phase1で指摘されたカラム名変更

### 3.1 変更対象テーブルと影響範囲

| テーブル名 | 旧カラム名 | 新カラム名 | 影響レコード数（推定） |
|-----------|-----------|-----------|-------------------|
| activity_logs | timestamp | created_at | 4件 |
| chat_history | timestamp | created_at | 不明 |
| answer_records | timestamp | created_at | 3,811件 |
| proficiency_records | last_updated | updated_at | 642件 |
| text_proficiency_records | last_updated | updated_at | 不明 |
| word_proficiency_records | last_updated | updated_at | 642件 |

**注意**: これらの変更はアプリケーションコードの修正も必要です。

## 4. データ整合性の修正

### 4.1 curriculum_units の権限修正
- `created_by`: 全て4 → 実際の教師ID（5, 18など）に修正
- `school_id`: 全てNULL → 適切な学校IDに修正
- `subject_id`: NULLの場合、元のカリキュラムから継承

### 4.2 unit_item_mappings の自動生成
- 教科と難易度レベルに基づいて問題を自動マッピング
- 初期は各単元に5-10問題を割り当て

### 4.3 student_unit_selections の進捗更新
- answer_recordsから実際の学習データを集計
- progress_percentage、completed_items、correct_itemsを更新
- statusを適切に設定（not_started/in_progress/completed）

## 5. マイグレーション実行手順

### 5.1 事前準備
1. **バックアップの取得**
   ```bash
   mysqldump -h [DB_HOST] -u [DB_USER] -p [DB_NAME] > backup_before_phase2.sql
   ```

2. **現在の状態確認**
   ```sql
   -- 影響を受けるテーブルのレコード数確認
   SELECT 'student_unit_selections' as table_name, COUNT(*) as count FROM student_unit_selections
   UNION ALL
   SELECT 'class_learning_settings', COUNT(*) FROM class_learning_settings
   UNION ALL
   SELECT 'answer_records', COUNT(*) FROM answer_records;
   ```

### 5.2 マイグレーション実行
1. **Phase1カラム名変更の確認と実行**
   ```bash
   mysql -h [DB_HOST] -u [DB_USER] -p [DB_NAME] < migrations/phase2_approval_workflow.sql
   ```

2. **データ整合性修正**
   ```bash
   mysql -h [DB_HOST] -u [DB_USER] -p [DB_NAME] < migrations/phase2_data_fixes.sql
   ```

### 5.3 実行後の確認
```sql
-- 新しいカラムの確認
SHOW COLUMNS FROM student_unit_selections LIKE 'approval%';
SHOW COLUMNS FROM class_learning_settings LIKE '%approval%';

-- データ分布の確認
SELECT approval_status, COUNT(*) FROM student_unit_selections GROUP BY approval_status;
```

## 6. ロールバック手順

問題が発生した場合：
```bash
mysql -h [DB_HOST] -u [DB_USER] -p [DB_NAME] < migrations/phase2_rollback.sql
```

## 7. パフォーマンスへの影響

### 7.1 インデックス追加による影響
- **メリット**: 承認待ちリストの表示が高速化
- **デメリット**: INSERT/UPDATE時のオーバーヘッドがわずかに増加

### 7.2 推奨事項
- 承認待ちが多い場合は、部分インデックスの活用を検討
- 定期的なインデックス統計の更新（ANALYZE TABLE）

## 8. セキュリティ考慮事項

- 承認権限のチェックをアプリケーション層で実装必要
- teacher_commentsやrejection_reasonのXSS対策
- 承認履歴の監査ログ実装を推奨

## 9. 今後の拡張可能性

- 承認履歴テーブルの追加
- 複数段階承認ワークフロー
- 承認通知機能（メール/アプリ内通知）
- 承認期限の設定

## 10. チェックリスト

### マイグレーション前
- [ ] バックアップ取得完了
- [ ] 影響範囲の確認完了
- [ ] アプリケーションコードの準備完了

### マイグレーション後
- [ ] 新規カラムの追加確認
- [ ] インデックスの作成確認
- [ ] データ整合性の確認
- [ ] アプリケーションの動作確認
- [ ] パフォーマンステスト実施

---
作成日: 2025-01-26
作成者: Claude Code Assistant