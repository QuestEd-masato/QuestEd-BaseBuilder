# Phase8C Stage2: 分解戦略設計書

**作成日時**: 2025年7月26日  
**対象ファイル**: 
1. `app/teacher/modules/curriculum_management.py` (1,209行) - 先行実施
2. `app/student/modules/dashboard.py` (1,249行) - 後続実施

---

## 🏗️ **Stage2-1: curriculum_management.py分解設計**

### **分解方針** (Phase8A成功パターン適用)
- **目標削減率**: 75%以上 (1,209行 → 300行以下)
- **サービス数**: 7個の専門サービス
- **ファサードパターン**: 100%後方互換性維持

### **専門サービス設計**

#### **1. CurriculumDataService** (推定250行)
```python
# app/services/curriculum/curriculum_data_service.py
責任範囲:
- 基本的なCRUD操作
- データ取得・更新
- 権限チェック統一

移行関数:
- view_curriculums() の一部
- view_curriculum() の一部
- delete_curriculum() の一部
- update_curriculum_info()
```

#### **2. CurriculumValidationService** (推定200行)
```python
# app/services/curriculum/curriculum_validation_service.py
責任範囲:
- 入力データ検証
- ビジネスルール検証
- 権限チェックヘルパー

移行ロジック:
- 各関数の権限チェック部分
- データ検証ロジック
- フォームバリデーション
```

#### **3. CurriculumAIService** (推定300行)
```python
# app/services/curriculum/curriculum_ai_service.py
責任範囲:
- AI統合処理
- generate_curriculum()のAI部分
- エラーハンドリング

移行ロジック:
- generate_curriculum()のAI呼び出し部分 (約100行)
- generate_curriculum_with_tasks()
- エラー時のフォールバック処理
```

#### **4. CurriculumImportExportService** (推定280行)
```python
# app/services/curriculum/curriculum_import_export_service.py
責任範囲:
- CSV/JSONインポート
- エクスポート処理
- テンプレート生成

移行関数:
- export_curriculum() (50行)
- import_curriculum() (66行)
- download_curriculum_template() (23行)
```

#### **5. LessonManagementService** (推定350行)
```python
# app/services/curriculum/lesson_management_service.py
責任範囲:
- レッスン管理全般
- タスク連携
- 進捗管理

移行関数:
- save_curriculum_lessons() (106行)
- edit_curriculum_lessons() (33行)
- get_curriculum_lessons_api() (30行)
```

#### **6. ThemeManagementService** (推定200行)
```python
# app/services/curriculum/theme_management_service.py
責任範囲:
- メインテーマCRUD
- テーマ・カリキュラム連携

移行関数:
- view_main_themes() (20行)
- create_main_theme() (49行)
- edit_main_theme() (42行)
- delete_main_theme() (33行)
```

#### **7. CurriculumUnitService** (推定250行)
```python
# app/services/curriculum/curriculum_unit_service.py
責任範囲:
- 単元変換・管理
- CurriculumBridgeService連携

移行関数:
- convert_curriculum_to_units() (34行)
- view_converted_units() (25行)
- edit_unit() (52行)
- delete_unit() (35行)
```

### **新curriculum_management.py** (推定280行)
```python
# app/teacher/modules/curriculum_management.py
責任範囲:
- Blueprintとルーティング
- ファサード実装
- テンプレートレンダリング

構造:
- 各エンドポイントは対応サービスに委譲
- 既存の関数シグネチャ完全維持
- エラーハンドリング統一
```

---

## 🏗️ **Stage2-2: dashboard.py分解設計**

### **分解方針**
- **目標削減率**: 75%以上 (1,249行 → 300行以下)
- **サービス数**: 5個の専門サービス + Phase6B既存3サービス活用
- **特記事項**: Phase6Bサービスとの調整必要

### **専門サービス設計**

#### **1. StudentMetricsService** (推定250行)
```python
# app/services/dashboard/student_metrics_service.py
責任範囲:
- 学生指標計算
- 統計処理
- 進捗率計算

移行関数:
- _generate_progress_stats() (55行)
- _generate_weekly_activity_stats() (49行)
- _get_difficulty_label() (9行)
```

#### **2. UnitProgressService** (推定400行)
```python
# app/services/dashboard/unit_progress_service.py
責任範囲:
- 単元進捗管理
- 学習進捗計算

移行関数:
- _generate_unit_stats() (211行) ★最大
- _get_learning_progress_summary() (187行) ★第2位
```

#### **3. BaseBuilderStatsService** (推定200行)
```python
# app/services/dashboard/basebuilder_stats_service.py
責任範囲:
- BaseBuilder統計
- WordProficiency連携

移行関数:
- _generate_basebuilder_stats() (171行) ★第3位
```

#### **4. ClassRankingService** (推定150行)
```python
# app/services/dashboard/class_ranking_service.py
責任範囲:
- クラスランキング
- トップ学習者計算

移行関数:
- _get_weekly_top_learners() (64行)
- get_class_top_learners() (58行)
```

#### **5. DashboardAPIService** (推定120行)
```python
# app/services/dashboard/dashboard_api_service.py
責任範囲:
- API用データ整形
- JSONレスポンス生成

移行関数:
- api_quick_stats() (44行)
- その他API関連ロジック
```

### **新dashboard.py** (推定280行)
```python
# app/student/modules/dashboard.py
責任範囲:
- Blueprintとルーティング
- Phase6Bサービス統合
- 新サービス統合

構造:
- dashboard()はオーケストレーション
- 各統計関数はサービスに委譲
- テンプレート連携維持
```

---

## 🔄 **実装順序とリスク管理**

### **Phase 1: curriculum_management.py分解** (先行)
```
理由: 影響範囲が教師限定で安全
手順:
1. 7サービスのスケルトン作成
2. 段階的にロジック移行
3. 各段階で動作確認
4. 最終統合テスト
```

### **Phase 2: dashboard.py分解** (後続)
```
理由: 学生全員に影響するため慎重に
手順:
1. Phase6Bサービスとの調整確認
2. 5サービスのスケルトン作成
3. 巨大関数から段階的移行
4. パフォーマンステスト実施
```

---

## ✅ **Stage2完了チェックリスト**

### **設計完了項目**
- ✅ Phase8A成功パターン適用
- ✅ 各サービスの責任範囲明確化
- ✅ 行数見積もり完了
- ✅ 実装順序決定

### **次のステップ (Stage3)**
1. curriculum_management.py向け7サービスのスケルトン作成
2. 段階的なロジック移行開始
3. 各段階での動作確認実施

**設計完了**: Phase8A成功パターンを完全適用した詳細設計が完成