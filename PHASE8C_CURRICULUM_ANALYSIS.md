# Phase8C Stage1-2: curriculum_management.py完全分析報告書

**分析日時**: 2025年7月26日  
**対象ファイル**: `app/teacher/modules/curriculum_management.py`  
**現在の行数**: 1,209行 (完全未着手)

---

## 📊 **ファイル構造分析**

### **1. 基本情報**
- **ファイルサイズ**: 48,963 bytes
- **作成日**: 2025年7月13日
- **Blueprint**: `teacher_curriculum_management`
- **場所**: app/teacher/modules/ (注意: api/ではない)

### **2. 主要関数一覧と行数**
```
巨大関数 (100行以上):
1. generate_curriculum(): 235行 ★最大 - AIカリキュラム生成
2. save_curriculum_lessons(): 106行 ★第2位 - レッスン保存

大規模関数 (50-99行):
3. edit_curriculum(): 97行 - カリキュラム編集
4. view_curriculum(): 72行 - カリキュラム表示
5. import_curriculum(): 66行 - CSV/JSONインポート
6. edit_unit(): 52行 - 単元編集
7. export_curriculum(): 50行 - エクスポート

中規模関数 (30-49行):
8. edit_main_theme(): 42行 - メインテーマ編集
9. view_curriculums(): 36行 - 一覧表示
10. update_curriculum_info(): 36行 - 情報更新
11. delete_unit(): 35行 - 単元削除
12. convert_curriculum_to_units(): 34行 - 単元変換
13. edit_curriculum_lessons(): 33行 - レッスン編集
14. delete_main_theme(): 33行 - テーマ削除
15. delete_curriculum(): 36行 - カリキュラム削除
16. get_curriculum_lessons_api(): 30行 - API

小規模関数 (30行未満):
17. create_curriculum_form(): 28行
18. view_converted_units(): 25行
19. download_curriculum_template(): 23行
20. view_main_themes(): 20行
21. create_main_theme(): 49行
```

### **3. APIエンドポイント構造**
```
カリキュラム管理:
- GET  /curriculums/<class_id> - 一覧表示
- GET  /curriculum/create/<class_id> - 作成フォーム
- POST /curriculum/generate/<class_id> - AI生成
- GET  /curriculum/<curriculum_id> - 詳細表示
- GET  /curriculum/<curriculum_id>/edit - 編集
- POST /curriculum/<curriculum_id>/delete - 削除
- GET  /curriculum/<curriculum_id>/export - エクスポート
- POST /curriculum/<class_id>/import - インポート

単元管理:
- POST /curriculum/<curriculum_id>/convert - 単元変換
- GET  /curriculum/<curriculum_id>/units - 単元一覧
- GET  /unit/<unit_id>/edit - 単元編集
- POST /unit/<unit_id>/delete - 単元削除

メインテーマ管理:
- GET  /themes/<class_id> - テーマ一覧
- POST /theme/create/<class_id> - テーマ作成
- GET  /theme/<theme_id>/edit - テーマ編集
- POST /theme/<theme_id>/delete - テーマ削除

レッスン管理:
- GET  /curriculum/<curriculum_id>/lessons/edit - レッスン編集
- POST /curriculum/<curriculum_id>/lessons/save - レッスン保存
- PUT  /curriculum/<curriculum_id>/update - 情報更新
- GET  /api/curriculum/<curriculum_id>/lessons - レッスンAPI
```

### **4. 主要な依存関係**

#### **モデル依存**:
- Class, Curriculum, CurriculumUnit
- MainTheme, ProblemCategory, Subject, User
- CurriculumLesson, LessonTask (レッスンシステム)
- StudentLessonProgress, StudentTaskCheck

#### **サービス依存**:
- `CurriculumBridgeService` - カリキュラム統合サービス
- `generate_curriculum_with_ai` - AI生成機能

#### **インポート元**:
- `app/teacher/__init__.py` - Blueprint登録

#### **テンプレート連携**:
- teacher/curriculum/*.html - 多数のテンプレート

---

## 🔍 **問題点分析**

### **1. 巨大関数問題**
- **generate_curriculum() (235行)**: AI生成の全処理を一つの関数で実行
  - フォームデータ処理
  - AI呼び出し
  - エラーハンドリング
  - レスポンス生成
- **save_curriculum_lessons() (106行)**: レッスン保存の複雑な処理

### **2. 責任の混在**
- APIエンドポイントとビジネスロジックの混在
- データ検証・権限チェック・DB操作が同一関数
- AI統合ロジックとフォーム処理の混在

### **3. 重複コード**
- 権限チェックが各関数で重複
- エラーハンドリングパターンの重複
- DB操作パターンの重複

---

## 📐 **分解戦略案**

### **提案サービス構造** (6-7個の専門サービス):

#### **1. CurriculumDataService** (データ管理専門)
- CRUD操作の基本処理
- データ取得・更新
- 単元変換処理

#### **2. CurriculumValidationService** (検証専門)
- 入力データ検証
- 権限チェック統一
- ビジネスルール検証

#### **3. CurriculumAIService** (AI統合専門)
- generate_curriculum()のAI部分分離
- AI呼び出しラッパー
- レスポンス整形

#### **4. CurriculumImportExportService** (インポート/エクスポート専門)
- CSVインポート処理
- JSONエクスポート処理
- テンプレート生成

#### **5. LessonManagementService** (レッスン管理専門)
- save_curriculum_lessons()の分解
- レッスン・タスク管理
- 進捗連携

#### **6. ThemeManagementService** (テーマ管理専門)
- メインテーマCRUD
- テーマ・カリキュラム連携

#### **7. CurriculumOrchestratorService** (統合制御)
- APIエンドポイント統合
- サービス間調整
- トランザクション管理

---

## ⚠️ **注意事項**

### **影響範囲**
1. **教師機能の中核**: カリキュラム作成・管理
2. **AI統合**: OpenAI API連携部分
3. **レッスンシステム**: 新システムとの統合部分

### **リスク要因**
1. **巨大関数の複雑性**: 235行のAI生成ロジック
2. **既存統合**: CurriculumBridgeServiceとの連携
3. **トランザクション**: 複数テーブル更新の整合性

---

## 🎯 **次のステップ**

### **Stage 1-2完了確認**
- ✅ ファイル構造分析完了
- ✅ 関数別行数分析完了
- ✅ APIエンドポイント一覧作成完了
- ✅ 依存関係特定完了

### **推奨アクション**
1. generate_curriculum()の詳細分析
2. save_curriculum_lessons()の内部ロジック確認
3. CurriculumBridgeServiceとの連携確認
4. テンプレート影響範囲の詳細確認

**分析結果**: curriculum_management.pyは教師機能の中核で、適切な分解により大幅な品質向上が期待できる