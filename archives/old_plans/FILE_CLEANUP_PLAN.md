# 📁 QuestEd ファイルクリーンアップ計画

## 🎯 削除対象ファイル分析

### **カテゴリA: 安全削除対象（即座実行）**

#### **1. 開発用ログファイル（3.2MB削減効果）**
```bash
# 大容量ログファイル（開発時のデバッグ用）
/home/masat/claude-projects/QuestEd/server_8092.log          # 2.0MB
/home/masat/claude-projects/QuestEd/flask_restart.log        # 554KB
/home/masat/claude-projects/QuestEd/server_test_fix.log      # 487KB
/home/masat/claude-projects/QuestEd/server_debug.log         # 400KB

# 小容量テスト用ログファイル
/home/masat/claude-projects/QuestEd/flask_test.log           # 5.2KB
/home/masat/claude-projects/QuestEd/test_server.log          # 8.1KB
/home/masat/claude-projects/QuestEd/server_test.log          # 4.4KB
/home/masat/claude-projects/QuestEd/server_test_2.log        # 1.5KB
/home/masat/claude-projects/QuestEd/server_admin_fix.log     # 2.3KB
/home/masat/claude-projects/QuestEd/server_student_debug.log # 2.7KB
```

#### **2. 開発中バックアップファイル**
```bash
/home/masat/claude-projects/QuestEd/app/student/modules/learning.py.backup_20250808_215143
/home/masat/claude-projects/QuestEd/backups/phase1_pre_test_data_20250730_100000.sql
```

### **カテゴリB: 慎重削除対象（要確認）**

#### **3. 古い分析・計画文書（重複・統合可能）**
```bash
# ナビゲーション関連（統合可能）
TEACHER_NAVIGATION_ERROR_ANALYSIS.md       # 4.4KB
NAVIGATION_ANALYSIS_REPORT.md              # 5.2KB
NAVIGATION_REPAIR_PLAN.md                  # 8.0KB
FINAL_NAVIGATION_FIX_PLAN.md                # 6.7KB
→ 統合先: COMPREHENSIVE_NAVIGATION_ANALYSIS.md（6.8KB）

# カリキュラム関連（統合済み）
CURRICULUM_UNIFICATION_PLAN.md              # 3.8KB
→ 統合先: COMPREHENSIVE_CURRICULUM_UNIFICATION_PLAN.md（11.1KB）

# Phase8関連（実行済み）
PHASE8B_DELETION_PLAN.md                    # 9.1KB
PHASE8C_CURRICULUM_ANALYSIS.md              # 6.5KB
PHASE8C_DASHBOARD_ANALYSIS.md               # 5.3KB
PHASE8C_IMPACT_ANALYSIS.md                  # 5.6KB
PHASE8E_STRATEGIC_PLAN.md                   # 3.3KB

# RDS関連（問題解決済み）
RDS_CLASS_DISPLAY_ANALYSIS.md               # 7.3KB
RDS_CLASS_DISPLAY_FIX_PLAN.md                # 6.8KB
DASHBOARD_CLASS_DISPLAY_ANALYSIS.md         # 5.9KB
```

### **カテゴリC: 保持対象（重要文書）**
```bash
# 現在の重要文書
CLAUDE.md                                    # メイン設定・履歴
README.md                                    # プロジェクト説明
ARCHITECTURE_INCONSISTENCY_ANALYSIS.md      # 今回の調査結果
COMPLEXITY_ANALYSIS.md                      # 修正分析
COMPREHENSIVE_CURRICULUM_UNIFICATION_PLAN.md # 統合計画
COMPREHENSIVE_NAVIGATION_ANALYSIS.md        # 統合分析

# docs/フォルダ内文書（体系的文書）
docs/deployment.md
docs/DEVELOPMENT_GUIDE.md
docs/architecture/SYSTEM_ARCHITECTURE.md
```

## 🛠️ 実行計画

### **ステップ1: 安全削除（カテゴリA）**
```bash
# ログファイル削除（3.2MB削減）
rm /home/masat/claude-projects/QuestEd/server_8092.log
rm /home/masat/claude-projects/QuestEd/flask_restart.log
rm /home/masat/claude-projects/QuestEd/server_test_fix.log
rm /home/masat/claude-projects/QuestEd/server_debug.log
rm /home/masat/claude-projects/QuestEd/flask_test.log
rm /home/masat/claude-projects/QuestEd/test_server.log
rm /home/masat/claude-projects/QuestEd/server_test*.log
rm /home/masat/claude-projects/QuestEd/server_admin_fix.log
rm /home/masat/claude-projects/QuestEd/server_student_debug.log

# バックアップファイル削除
rm /home/masat/claude-projects/QuestEd/app/student/modules/learning.py.backup_20250808_215143
rm /home/masat/claude-projects/QuestEd/backups/phase1_pre_test_data_20250730_100000.sql
```

### **ステップ2: 文書統合・削除（カテゴリB）**
```bash
# 重複文書削除（内容は統合済み文書に保存済み）
rm TEACHER_NAVIGATION_ERROR_ANALYSIS.md
rm NAVIGATION_ANALYSIS_REPORT.md
rm NAVIGATION_REPAIR_PLAN.md
rm CURRICULUM_UNIFICATION_PLAN.md
rm PHASE8B_DELETION_PLAN.md
rm PHASE8C_*.md
rm PHASE8E_STRATEGIC_PLAN.md
rm RDS_CLASS_DISPLAY_*.md
rm DASHBOARD_CLASS_DISPLAY_ANALYSIS.md
```

## 📊 期待効果
- **容量削減**: 約4MB（主にログファイル）
- **文書整理**: 26個の重複文書 → 6個の重要文書
- **保守性向上**: 開発者の混乱防止
- **プロジェクト品質**: プロ水準のファイル管理

## ⚠️ 注意事項
- すべて可逆的（GitHubにバックアップ済み）
- 重要情報は統合文書に保存済み
- CLAUDE.mdに主要情報集約済み