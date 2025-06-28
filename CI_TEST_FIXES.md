# QuestEd テストエラー修正ガイド

## 🔍 **発見された問題**

リファクタリング後のテストエラーは以下の原因で発生しています：

### 1. **テンプレート内のurl_for参照の更新不足**
```html
<!-- 修正前 -->
{{ url_for('teacher.dashboard') }}

<!-- 修正後 -->
{{ url_for('teacher_dashboard.dashboard') }}
```

### 2. **Python内のインポート参照の更新不足**
```python
# 修正前
from app.teacher import _generate_class_analytics

# 修正後
from app.teacher.modules.analytics import _generate_class_analytics
```

### 3. **ルートの重複定義**
同じパスが複数のBlueprintで定義されている可能性

## 🛠️ **修正方法**

### **自動修正スクリプトの実行**
```bash
# 1. テストエラー修正スクリプト実行
python fix_test_issues.py

# 2. 修正後のテスト実行
python run_tests.py
```

### **手動修正が必要な場合**

#### **1. テンプレートの修正**
以下のパターンで検索・置換：

```bash
# 教師関連
teacher.dashboard → teacher_dashboard.dashboard
teacher.classes → teacher_class_management.classes
teacher.teacher_themes → teacher_student_evaluation.teacher_themes

# 学生関連
student.dashboard → student_dashboard.dashboard
student.activities → student_activities.activities
student.surveys → student_surveys.surveys
student.goals → student_goals_todos.goals
student.todos → student_goals_todos.todos
```

#### **2. Python インポートの修正**
```python
# app/api/__init__.py の修正例
from app.teacher.modules.analytics import _generate_class_analytics

# その他のインポートも同様にモジュール別に修正
```

## 📋 **実装されたテスト**

### **1. 基本テスト (`run_tests.py`)**
- インポートテスト
- ルート登録テスト
- モジュール分割テスト
- データベースモデルテスト
- API機能テスト
- Phase 3 データ整合性テスト

### **2. ユニットテスト (`tests/unit/test_refactoring.py`)**
- 教師機能のリファクタリングテスト
- 学生機能のリファクタリングテスト
- API機能のリファクタリングテスト
- Phase 3 データ整合性テスト
- インポート互換性テスト
- ルート重複チェック

### **3. テストフィクスチャ (`tests/conftest_fixtures.py`)**
- admin_user, teacher_user, student_user
- sample_subject, sample_unit, sample_class
- テスト用データベースセットアップ

## 🚀 **CI/CD環境での対応**

### **GitHubアクション等での実行**
```yaml
# .github/workflows/test.yml (例)
steps:
  - name: Fix test issues
    run: python fix_test_issues.py
    
  - name: Run tests
    run: python run_tests.py
    
  - name: Run pytest
    run: pytest tests/ -v
```

### **依存関係の確認**
```bash
# 必要なパッケージがインストールされているか確認
pip list | grep -E "(flask|pytest|sqlalchemy)"
```

## ✅ **修正完了チェックリスト**

- [ ] `fix_test_issues.py` 実行済み
- [ ] `run_tests.py` で全テスト通過
- [ ] テンプレート内の `url_for` 参照更新済み
- [ ] Python内のインポート参照更新済み
- [ ] ルート重複が解消済み
- [ ] Blueprint名前空間が正しく設定済み
- [ ] 後方互換性が維持済み

## 🔧 **トラブルシューティング**

### **よくあるエラーと解決法**

#### **1. "No module named 'flask'"**
```bash
# 解決法: 仮想環境の有効化または依存関係インストール
pip install -r requirements.txt
```

#### **2. "Template not found"**
```bash
# 解決法: テンプレートパスの確認
ls -la templates/teacher/
ls -la templates/student/
```

#### **3. "Route already registered"**
```bash
# 解決法: ルート重複の確認・修正
python -c "from app import create_app; app = create_app(); print([r for r in app.url_map.iter_rules()])"
```

#### **4. "ImportError: cannot import name"**
```bash
# 解決法: インポートパスの確認・修正
# モジュール構造を確認
find app/ -name "*.py" | grep -E "(teacher|student)" | head -10
```

## 📊 **修正後の期待される状態**

1. **✅ 全テストが通過**
2. **✅ ルート重複なし**
3. **✅ インポートエラーなし**
4. **✅ テンプレートエラーなし**
5. **✅ 後方互換性維持**
6. **✅ Blueprint正常動作**

## 📝 **継続的メンテナンス**

新しい機能追加時は以下を確認：
- Blueprint名前空間の一貫性
- url_for参照の正確性
- インポートパスの正確性
- テストカバレッジの維持