# Phase8C Stage1-3: 依存関係影響分析報告書

**分析日時**: 2025年7月26日  
**対象ファイル**: 
- `app/student/modules/dashboard.py` (1,249行)
- `app/teacher/modules/curriculum_management.py` (1,209行)

---

## 🔗 **依存関係マップ**

### **dashboard.py依存関係**

#### **呼び出し元**:
```
Blueprint登録:
└── app/student/__init__.py
    └── dashboard_bp → Flask App

テンプレート参照 (10+件):
├── student/task_submit.html
├── student/task_submission.html
├── student/unit_completion_request.html
├── student/task_work.html
├── student/debug_routes.html
├── student/task_list.html
├── student/curriculum_tasks.html
├── student/lesson_detail.html
├── student/class_themes.html
└── student/class_details.html
```

#### **サービス依存** (Phase6B):
```
既存サービス:
├── DashboardService (app/services/dashboard_service.py)
├── DashboardRendererService (app/services/dashboard_renderer.py)
└── StudentInfoService (app/services/student_info_service.py)

外部サービス参照:
└── BaseBuilderTaskService (445行目で動的インポート)
```

#### **モデル依存**:
- 15個以上のモデル (ActivityLog, ChatHistory, Class等)
- BaseBuilder関連: WordProficiency

### **curriculum_management.py依存関係**

#### **呼び出し元**:
```
Blueprint登録:
└── app/teacher/__init__.py
    └── curriculum_management_bp → Flask App

テンプレート参照:
├── teacher/curriculum_lesson_editor.html
├── teacher/integrated_management.html
└── teacher/dashboard.html
```

#### **サービス依存**:
```
既存サービス:
└── CurriculumBridgeService (app/services/curriculum_bridge_service.py)
    - get_conversion_status()
    - convert_curriculum_to_units()

AI統合:
└── generate_curriculum_with_ai (app/ai/)
```

#### **モデル依存**:
- 8個のコアモデル (Class, Curriculum, CurriculumUnit等)
- レッスンシステム: CurriculumLesson, LessonTask等

---

## 🎯 **影響範囲分析**

### **dashboard.py分解の影響**

#### **高リスク要因**:
1. **高頻度アクセス**: 学生ログイン後の主画面
2. **テンプレート連携**: 10個以上のテンプレートから参照
3. **リアルタイムデータ**: 進捗・統計の即時表示要求

#### **中リスク要因**:
1. **Phase6Bサービス**: 既存3サービスとの調整必要
2. **BaseBuilder統合**: 動的インポートの処理
3. **パフォーマンス**: 複数DB問い合わせの最適化

#### **低リスク要因**:
1. **Blueprint独立性**: 他モジュールへの影響最小
2. **ファサード適用可**: 既存関数シグネチャ維持可能

### **curriculum_management.py分解の影響**

#### **高リスク要因**:
1. **AI統合**: OpenAI API呼び出しの複雑性
2. **トランザクション**: 複数テーブル同時更新
3. **権限管理**: 教師権限の厳密なチェック

#### **中リスク要因**:
1. **CurriculumBridgeService**: 既存統合の維持
2. **レッスンシステム**: 新旧システムの共存
3. **インポート/エクスポート**: ファイル処理の複雑性

#### **低リスク要因**:
1. **教師限定機能**: 影響ユーザー数限定
2. **独立性高**: 他モジュールとの結合度低

---

## 📊 **リスク評価マトリクス**

### **分解優先度評価**

| ファイル | 影響度 | 複雑度 | リスク | 優先度 |
|---------|--------|--------|--------|--------|
| dashboard.py | 高 (学生全員) | 高 (1,249行) | 中-高 | **1位** |
| curriculum_management.py | 中 (教師のみ) | 高 (1,209行) | 中 | **2位** |

### **推奨分解順序**
1. **curriculum_management.py先行** - 影響範囲が限定的
2. **dashboard.py後続** - より慎重な実行が必要

---

## 🛡️ **リスク軽減策**

### **共通対策**
1. **完全バックアップ**: 各段階での保存
2. **ファサードパターン**: 100%後方互換性
3. **段階的テスト**: 各サービス個別確認
4. **ロールバック準備**: 即座復旧体制

### **dashboard.py特有対策**
1. **パフォーマンステスト**: レスポンス時間計測
2. **Phase6Bサービス調整**: 既存サービスとの連携確認
3. **テンプレート影響確認**: 全10箇所の動作テスト

### **curriculum_management.py特有対策**
1. **AI呼び出しモック**: 開発時のAPI呼び出し削減
2. **トランザクション確認**: DB整合性テスト
3. **権限テスト**: 教師権限の網羅的確認

---

## 🎯 **Stage 1-3完了確認**

### **完了項目**
- ✅ 両ファイルの依存関係マップ作成
- ✅ テンプレート影響範囲特定
- ✅ サービス連携状況確認
- ✅ リスク評価・優先度決定

### **重要な発見**
1. **Phase6Bサービス**: dashboard.pyは既に部分的にサービス化済み
2. **影響範囲の差**: curriculum_management.pyの方が影響限定的
3. **Phase8A知見活用**: unitサービスパターンが参考になる

### **推奨事項**
- **実行順序**: curriculum_management.py → dashboard.py
- **Phase8A成功パターン**: 8サービス分割の実績を完全活用
- **既存サービス活用**: Phase6B/8Aの成果を最大限利用

**Stage 1分析完了**: 両ファイルの完全な現状把握と影響分析が完了