# 🔍 レッスン関連問題・データベース最適化 詳細調査計画

## 📊 現状分析結果

### **問題①: 学生レッスンアクセスエラー解析**

#### **技術スタック構造**
```
学生レッスンポータル階層:
├── /student/learning (Flask Route)
├── learning_portal.html (Template)  
├── learning.py (Controller)
├── lesson_models.py (Models - 遅延インポート)
├── CurriculumMigrationAdapter (Data Integration)
└── JavaScript/AJAX (Frontend Logic)
```

#### **発見された潜在的問題点**
1. **遅延インポートの複雑性**: `_import_lesson_models()` による動的モデル読み込み
2. **データソース二重化**: `curriculum_lessons` vs `curriculum_data` (JSON)
3. **例外処理の多層化**: 各段階での try/except による エラーマスキング
4. **進捗計算の複雑性**: Phase5 承認システム統合による条件分岐増加

### **問題②: カリキュラム編集保存問題解析**

#### **技術スタック構造**  
```
カリキュラム編集システム階層:
├── /teacher/curriculum/{id}/edit (Flask Route)
├── curriculum_edit.html (Template + JavaScript)
├── curriculum_management.py (Controller)
├── curriculum_orchestration_service.py (Service Layer)
├── curriculum_lesson_direct.py (API Layer)
└── curriculum_data_service.py (Data Layer)
```

#### **発見された潜在的問題点**
1. **サービス層過剰化**: 5つの類似カリキュラムサービスによる責任分散
2. **フォーム処理複雑化**: `table_content_data` のJSON変換処理
3. **同期処理問題**: JSON ↔ テーブル間の複雑な同期処理
4. **CSS競合可能性**: `button-overrides.css` の !important 規則

---

## 🎯 優先度1: レッスン関連問題調査計画

### **1. JavaScript/AJAX エラー確認計画**

#### **調査対象ファイル**
```bash
# フロントエンド調査
templates/student/learning_portal.html     # メインテンプレート
static/js/main.js                         # メインJavaScript
static/js/mobile.js                       # モバイル対応
static/js/realtime-sync.js                # リアルタイム同期
```

#### **調査手順**
1. **ブラウザ開発者ツール分析**:
   ```javascript
   // 確認項目
   - Console エラーログ
   - Network タブでのAJAX失敗
   - Elements タブでのDOM構築状況
   - Application タブでの LocalStorage/Session 状況
   ```

2. **JavaScript エラーパターン識別**:
   ```javascript
   // よくあるエラーパターン
   - "Uncaught ReferenceError: xxx is not defined"
   - "Failed to fetch" (AJAX通信エラー)
   - "Cannot read property 'xxx' of undefined"
   - "JSON.parse unexpected token" (データ解析エラー)
   ```

3. **AJAX通信ログ分析**:
   ```bash
   # サーバーログでの確認項目
   tail -f /var/log/nginx/access.log | grep "/student/learning"
   journalctl -u quested.service -f | grep "learning"
   ```

#### **期待される発見**
- フロントエンド・バックエンド間の通信断絶点
- データ形式不整合によるJavaScriptエラー
- 非同期処理のタイミング問題

### **2. API エンドポイント調査計画**

#### **調査対象ルート**
```python
# 学習ポータル関連エンドポイント
/student/learning                    # メイン学習ポータル  
/api/lesson-system/curriculum/{id}   # カリキュラムAPI
/api/lesson-system/progress/{id}     # 進捗取得API
```

#### **調査手順**  
1. **直接API応答テスト**:
   ```bash
   # Production環境でのAPI直接テスト
   curl -H "Cookie: session=xxx" https://quest-ed.jp/student/learning
   curl -H "Cookie: session=xxx" https://quest-ed.jp/api/lesson-system/curriculum/14
   ```

2. **レスポンスデータ構造確認**:
   ```python
   # 期待レスポンス vs 実際レスポンス比較
   {
     "success": true/false,
     "available_curricula": [...],
     "my_progress": [...],
     "error": "..." # エラー時のみ
   }
   ```

3. **ログベース分析**:
   ```bash
   # API呼び出しのサーバーサイドログ
   ssh ec2-user@13.113.164.85 "journalctl -u quested.service -n 100 | grep -E '(learning|curriculum|lesson)'"
   ```

#### **期待される発見**
- API応答の不整合（空レスポンス、エラーレスポンス）
- データベースクエリエラーによるサーバーサイド障害
- 権限チェック問題による認証エラー

### **3. CSS 競合調査計画**

#### **調査対象ファイル**
```css
/* CSS競合調査対象 */
static/css/button-overrides.css      # !important 多用ファイル
static/css/modern-responsive.css     # メインスタイル
static/css/curriculum.css            # カリキュラム専用スタイル
templates/teacher/curriculum_edit.html # インラインスタイル
```

#### **調査手順**
1. **CSS Cascade 分析**:
   ```css
   /* 保存ボタンの競合確認 */
   .btn-primary { /* base style */ }
   .btn.btn-primary { /* button-override */ }
   .container .btn-primary { /* 詳細度による上書き */ }
   form .btn-primary !important { /* 強制上書き */ }
   ```

2. **開発者ツールでのスタイル競合確認**:
   ```javascript
   // Elements > Styles パネルで確認
   - 取り消し線スタイル（上書きされたルール）
   - 最終適用値
   - !important の影響範囲
   ```

3. **機能的影響確認**:
   ```css
   /* 保存ボタン無効化の可能性 */
   pointer-events: none;        /* クリック無効化 */
   opacity: 0.6;               /* 半透明化 */
   z-index: -1;                /* 表示層競合 */
   ```

#### **期待される発見**
- 保存ボタンのクリックイベント阻害
- フォーム要素の視覚的・機能的無効化
- レスポンシブ対応による意図しないスタイル継承

### **4. サービス層循環参照調査計画**

#### **調査対象サービス**
```python
# 循環参照調査対象
app/modules/lesson_system/services/   # レッスンシステム
app/services/curriculum/              # カリキュラム管理  
app/services/student_dashboard/       # ダッシュボード
app/services/dashboard/               # 全般ダッシュボード
```

#### **調査手順**
1. **インポート依存関係マップ作成**:
   ```bash
   # Python インポートグラフ作成
   find app/ -name "*.py" -exec grep -l "from.*lesson" {} \; | head -20
   find app/ -name "*.py" -exec grep -l "import.*curriculum" {} \; | head -20
   ```

2. **遅延インポート問題確認**:
   ```python
   # _get_lesson_models() パターンの重複確認
   grep -r "_get_lesson_models" app/
   grep -r "lesson_models not available" app/
   ```

3. **初期化順序問題確認**:
   ```python
   # アプリケーション起動時のインポート順序
   python -c "
   import sys
   sys.path.append('/var/www/quested/QuestEd')
   from app import create_app
   create_app()
   " 2>&1 | grep -E "(Import|Error|Warning)"
   ```

#### **期待される発見**
- 循環インポートによるモデル初期化失敗
- 遅延インポートの失敗による機能不全
- アプリケーション起動時の依存関係エラー

---

## 🎯 優先度2: データベース最適化計画

### **1. 軽微クリーンアップ計画**

#### **Phase 1: 不要データ特定**
```sql
-- テストデータ・開発データの特定
SELECT 'activity_logs テストデータ' as category, COUNT(*) as count
FROM activity_logs WHERE content LIKE '%test%' OR content LIKE '%テスト%';

SELECT 'users 開発アカウント' as category, COUNT(*) as count  
FROM users WHERE email LIKE '%test%' OR email LIKE '%dev%';

SELECT '孤立レコード' as category, COUNT(*) as count
FROM student_lesson_progress slp 
LEFT JOIN users u ON slp.student_id = u.id
WHERE u.id IS NULL;
```

#### **Phase 2: インデックス使用状況分析**  
```sql
-- インデックス効率性確認
SELECT 
    TABLE_NAME,
    INDEX_NAME, 
    CARDINALITY,
    SUB_PART,
    NON_UNIQUE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'quested'
ORDER BY TABLE_NAME, SEQ_IN_INDEX;
```

#### **Phase 3: 使用されていないカラム調査**
```python
# アプリケーションコードでの未使用カラム確認
columns_to_check = [
    'mastery_threshold',      # curriculum_units
    'self_paced_mode',        # curriculum_units  
    'prerequisite_skills',    # curriculum_units
]

# コード内での参照確認
for column in columns_to_check:
    grep -r {column} app/ || echo "Column {column} not referenced"
```

### **2. カリキュラム統一計画**

#### **現状の二重管理構造**
```python
# データソース1: JSON形式
curriculum.curriculum_data = {
    "table_content": [
        {"item": "レッスン1", "time": 50, ...},
        {"item": "レッスン2", "time": 60, ...}
    ]
}

# データソース2: テーブル形式  
curriculum_lessons = CurriculumLesson.query.filter_by(
    curriculum_id=curriculum.id
).all()
```

#### **統一アプローチ**
1. **Phase 1: 移行準備**
   - データ整合性確認
   - バックアップ作成
   - 移行スクリプト作成

2. **Phase 2: 段階的移行**
   - JSON → テーブル 変換ツール
   - 両方式並行動作期間
   - 徐々にテーブル形式優先

3. **Phase 3: JSON 廃止**
   - テーブル形式完全移行
   - 同期処理サービス削除
   - パフォーマンス測定

#### **期待効果**
- **コード削減**: 30% (同期処理削除)
- **パフォーマンス向上**: 30-40% (単一データソース)  
- **保守性向上**: 複雑性大幅削減

---

## ⚠️ リスク評価・注意事項

### **高リスク項目**
1. **カリキュラム統一**: 既存データの完全性保証が必要
2. **サービス層修正**: 複数サービスの同期修正が必要
3. **CSS修正**: 全テンプレートへの影響範囲確認が必要

### **低リスク項目**  
1. **JavaScript調査**: 読み取り専用の調査
2. **ログ分析**: システムへの影響なし
3. **軽微DB最適化**: 可逆的操作のみ

### **推奨実施順序**
1. **調査フェーズ**: すべての調査を並行実施（リスクなし）
2. **軽微修正**: JavaScript・CSS問題の個別修正
3. **構造修正**: サービス層・データベース統合（慎重に段階実施）

この計画により、レッスン関連問題の根本原因を特定し、データベース最適化を安全かつ効果的に実施できます。