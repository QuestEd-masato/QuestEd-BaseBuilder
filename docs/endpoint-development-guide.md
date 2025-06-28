# QuestEd エンドポイント開発ガイド

## 概要
このガイドでは、QuestEdでのFlask Blueprintとurl_for()の正しい使用方法を説明します。

## Blueprint構造

### 現在のBlueprint階層

#### メインBlueprint
```python
# app/__init__.py で登録
auth_bp = Blueprint('auth', __name__)           # 認証
admin_bp = Blueprint('admin_panel', __name__)   # 管理
api_bp = Blueprint('api', __name__)             # API
realtime_bp = Blueprint('realtime', __name__)   # リアルタイム機能
```

#### モジュール化されたBlueprint（teacher/student）
```python
# app/teacher/__init__.py で定義、register_teacher_blueprints(app)で登録
teacher_bp = Blueprint('teacher', __name__)                           # メイン
teacher_dashboard_bp = Blueprint('teacher_dashboard', __name__)       # ダッシュボード
teacher_class_management_bp = Blueprint('teacher_class_management', __name__)
teacher_curriculum_management_bp = Blueprint('teacher_curriculum_management', __name__)
teacher_student_evaluation_bp = Blueprint('teacher_student_evaluation', __name__)
teacher_analytics_bp = Blueprint('teacher_analytics', __name__)
teacher_approval_workflow_bp = Blueprint('teacher_approval_workflow', __name__)
teacher_synchronization_bp = Blueprint('teacher_synchronization', __name__)

# app/student/__init__.py で定義、register_student_blueprints(app)で登録
student_bp = Blueprint('student', __name__)                     # メイン
student_dashboard_bp = Blueprint('student_dashboard', __name__)  # ダッシュボード
student_activities_bp = Blueprint('student_activities', __name__)
student_surveys_bp = Blueprint('student_surveys', __name__)
student_goals_todos_bp = Blueprint('student_goals_todos', __name__)
```

#### BaseBuilderBlueprint
```python
# basebuilder/routes/__init__.py で定義、register_basebuilder_routes(app)で登録
basebuilder_module = Blueprint('basebuilder_module', __name__)  # メイン
basebuilder_admin_bp = Blueprint('basebuilder_admin', __name__)
categories_bp = Blueprint('categories', __name__)
problems_bp = Blueprint('problems', __name__)
sessions_bp = Blueprint('sessions', __name__)
progress_bp = Blueprint('progress', __name__)
analytics_bp = Blueprint('analytics', __name__)
```

## 正しいurl_for()の使用方法

### 基本原則
1. **Blueprint名.関数名** の形式で記述
2. Blueprint名は登録時の名前を使用（変数名ではない）
3. 関数名は実際に定義された関数名を使用

### よく使用されるエンドポイント

#### 認証関連
```python
url_for('auth.login')           # ログインページ
url_for('auth.logout')          # ログアウト  
url_for('auth.register')        # 登録ページ
url_for('auth.profile')         # プロフィールページ
```

#### ダッシュボード
```python
url_for('admin_panel.dashboard')        # 管理者ダッシュボード
url_for('teacher_dashboard.dashboard')  # 教師ダッシュボード
url_for('student_dashboard.dashboard')  # 学生ダッシュボード
```

#### 学生機能
```python
url_for('student_activities.activities')  # 活動記録
url_for('student_surveys.surveys')        # アンケート
url_for('student_goals_todos.goals')      # 目標管理
url_for('student_goals_todos.todos')      # TODO管理
```

#### BaseBuilder機能
```python
url_for('basebuilder_module.index')         # BaseBuilderホーム
url_for('basebuilder_admin.learning_paths') # 学習パス管理
url_for('categories.categories')            # カテゴリ管理
url_for('problems.problems')                # 問題管理
```

#### その他
```python
url_for('index')                    # アプリケーションルート
url_for('static', filename='...')   # 静的ファイル
```

## 開発時の注意点

### 1. 新しいBlueprint作成時
```python
# ✅ 正しい方法
new_bp = Blueprint('feature_module', __name__)

@new_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# テンプレートでの使用
# {{ url_for('feature_module.dashboard') }}
```

### 2. Blueprint名の確認方法
```bash
# すべてのBlueprint名を確認
grep -r "Blueprint(" app/ basebuilder/ --include="*.py" | grep -v "__pycache__"

# 特定のBlueprint名の使用箇所を確認
grep -r "url_for('feature_module" . --include="*.py" --include="*.html"
```

### 3. テンプレートでの注意点
```html
<!-- ✅ 正しい方法 -->
<a href="{{ url_for('student_dashboard.dashboard') }}">ダッシュボード</a>

<!-- ❌ 間違った方法 -->
<a href="{{ url_for('student.dashboard') }}">ダッシュボード</a>

<!-- ✅ 条件分岐での使用 -->
{% if request.path == url_for('admin_panel.dashboard') %}active{% endif %}

<!-- ❌ 間違った方法 -->
{% if request.path == {{ url_for('admin_panel.dashboard') }} %}active{% endif %}
```

## 自動検証ツール

### エンドポイント整合性チェック
```bash
# 修正後の検証実行
python3 verify_endpoint_fixes.py

# Blueprint重複チェック
python3 -c "
import re
from pathlib import Path
blueprints = {}
for py_file in Path('.').rglob('*.py'):
    if '__pycache__' not in str(py_file):
        try:
            content = py_file.read_text()
            matches = re.findall(r\"Blueprint\('([^']+)'\", content)
            for bp_name in matches:
                blueprints.setdefault(bp_name, []).append(str(py_file))
        except: pass
for name, files in blueprints.items():
    if len(files) > 1:
        print(f'DUPLICATE: {name} in {files}')
"
```

## トラブルシューティング

### よくあるエラーと解決方法

#### 1. BuildError: Could not build url for endpoint 'xxx'
```
原因: エンドポイント名が間違っている
解決: 正しいBlueprint名.関数名を確認
```

#### 2. TemplateAssertionError  
```
原因: テンプレート構文エラー
解決: {{ }} の対応を確認
```

#### 3. Blueprint already registered
```
原因: Blueprint名の重複
解決: 一意のBlueprint名を使用
```

### デバッグ用コマンド
```python
# Flask shellでエンドポイント一覧を確認
flask shell
>>> from app import create_app
>>> app = create_app()
>>> with app.app_context():
...     for rule in app.url_map.iter_rules():
...         print(f"{rule.endpoint} -> {rule}")
```

## CI/CDでの自動チェック

### pre-commitフック例
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking Blueprint consistency..."
python3 verify_endpoint_fixes.py > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Blueprint consistency check failed"
    exit 1
fi

echo "✅ Blueprint consistency check passed"
```

### GitHub Actions例
```yaml
name: Endpoint Validation
on: [push, pull_request]

jobs:
  validate-endpoints:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate endpoints
        run: python3 verify_endpoint_fixes.py
```

## 追加リソース

- [Flask Blueprint Documentation](https://flask.palletsprojects.com/en/2.0.x/blueprints/)
- [QuestEd Blueprint Naming Convention](./blueprint-naming-convention.md)
- [QuestEd Architecture Overview](./architecture.md)

---

**更新履歴:**
- 2025-06-28: 初版作成（大規模リファクタリング後の統合）
- URL修正件数: 199箇所、対象ファイル: 59個