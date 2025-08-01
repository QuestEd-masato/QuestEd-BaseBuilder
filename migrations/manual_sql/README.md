# Manual SQL Files

このディレクトリには手動で作成されたSQLファイルが含まれています。
これらは段階的にAlembicマイグレーションに統合する予定です。

## ファイル一覧：
total 76
drwxr-xr-x 2 masat masat 4096 Jul 31 10:40 .
drwxr-xr-x 6 masat masat 4096 Jul 31 10:40 ..
-rw-r--r-- 1 masat masat 5072 Jul 21 07:12 add_mfa_tables.sql
-rw-r--r-- 1 masat masat 1670 Jul 16 10:27 add_resubmission_count.sql
-rw-r--r-- 1 masat masat 3623 Jul 10 17:37 add_self_paced_learning_fields.sql
-rw-r--r-- 1 masat masat 5577 Jul 11 06:56 create_task_tables.sql
-rw-r--r-- 1 masat masat 4505 Jun 18 16:20 init_curriculum_tables.sql
-rw-r--r-- 1 masat masat 7961 Jun 26 16:42 phase2_approval_workflow.sql
-rw-r--r-- 1 masat masat 6113 Jun 26 16:43 phase2_data_fixes.sql
-rw-r--r-- 1 masat masat 3629 Jun 26 16:43 phase2_rollback.sql
-rw-r--r-- 1 masat masat 3701 Jul 25 18:40 phase5_lesson_approval_workflow.sql
-rw-r--r-- 1 masat masat 5050 Jul 30 10:08 restore_lesson_system_tables.sql
-rw-r--r-- 1 masat masat 3528 Jul  3 01:37 sql_ranking_repair.sql

## 注意：
- これらのファイルは直接実行しないでください
- Alembicとの整合性を確認してから適用してください
- 本番環境では必ずバックアップを取ってから実行してください

