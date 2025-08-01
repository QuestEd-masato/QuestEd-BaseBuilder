# QuestEd テストガイド

<div align="center">
  <h3>🧪 QuestEd 包括的テスト戦略ガイド</h3>
  <p>
    <a href="#テスト戦略">テスト戦略</a> •
    <a href="#環境設定">環境設定</a> •
    <a href="#ユニットテスト">ユニットテスト</a> •
    <a href="#統合テスト">統合テスト</a> •
    <a href="#e2eテスト">E2Eテスト</a>
  </p>
</div>

---

## 📋 テスト戦略

### テストピラミッド

QuestEdでは以下のテスト構造を採用しています：

```
        /\
       /  \
      / E2E \     少数・高価値・低速
     /______\
    /        \
   /   統合   \    中程度・重要・中速
  /___________\
 /             \
/  ユニット     \   多数・高速・詳細
/______________\
```

### テストカバレッジ目標

| テストレベル | 目標カバレッジ | 実行頻度 |
|-------------|---------------|----------|
| **ユニットテスト** | 90%+ | 全コミット |
| **統合テスト** | 80%+ | 全プルリクエスト |
| **E2Eテスト** | 主要機能100% | リリース前 |

---

## ⚙️ テスト環境の設定

### 前提条件

```bash
# テスト用Pythonパッケージのインストール
pip install pytest pytest-cov pytest-mock pytest-flask selenium
pip install factory-boy faker coverage
```

### テスト用環境変数

```bash
# .env.testingファイルを作成
cp .env.example .env.testing

# テスト用設定を編集
FLASK_ENV=testing
DATABASE_NAME=quested_test
TESTING=True
WTF_CSRF_ENABLED=False
```

### テストデータベースの準備

```bash
# テスト用データベースの作成
mysql -u root -p -e "CREATE DATABASE quested_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# テスト用ユーザーの作成
mysql -u root -p -e "GRANT ALL PRIVILEGES ON quested_test.* TO 'quested_user'@'localhost';"

# テストマイグレーション
export FLASK_ENV=testing
flask db upgrade
```

---

## 🔬 ユニットテスト

### テストファイル構造

```
tests/
├── unit/
│   ├── __init__.py
│   ├── conftest.py           # pytest設定・フィクスチャ
│   ├── test_models.py        # モデルテスト
│   ├── test_services.py      # サービス層テスト
│   ├── test_utils.py         # ユーティリティテスト
│   └── modules/
│       ├── test_auth.py      # 認証モジュール
│       ├── test_mfa.py       # MFAテスト
│       └── test_ai.py        # AI機能テスト
├── integration/
└── e2e/
```

### 基本的なテストの書き方

#### 1. モデルテスト例

```python
# tests/unit/test_models.py
import pytest
from app.models import User, Goal, Todo

class TestUserModel:
    def test_create_user(self, app):
        """ユーザー作成のテスト"""
        with app.app_context():
            user = User(
                username='test_user',
                email='test@example.com',
                role='student'
            )
            user.set_password('secure_password')
            
            assert user.username == 'test_user'
            assert user.check_password('secure_password')
            assert not user.check_password('wrong_password')

    def test_user_repr(self, app):
        """ユーザー文字列表現のテスト"""
        with app.app_context():
            user = User(username='test_user')
            assert str(user) == '<User test_user>'

class TestGoalModel:
    def test_goal_creation(self, sample_user):
        """目標作成のテスト"""
        goal = Goal(
            student_id=sample_user.id,
            title='数学の成績向上',
            description='次回テストで80点以上を目指す',
            progress=0
        )
        
        assert goal.title == '数学の成績向上'
        assert goal.progress == 0
        assert not goal.is_completed

    def test_goal_completion(self, sample_goal):
        """目標完了のテスト"""
        sample_goal.progress = 100
        
        assert sample_goal.is_completed is True
```

#### 2. サービステスト例

```python
# tests/unit/test_services.py
import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import AIService

class TestAIService:
    def test_generate_response(self):
        """AI応答生成のテスト"""
        with patch('app.ai.generate_chat_response') as mock_ai:
            mock_ai.return_value = "これは良い質問ですね。"
            
            service = AIService()
            response = service.generate_response("数学について教えて", "math")
            
            assert response == "これは良い質問ですね。"
            mock_ai.assert_called_once_with("数学について教えて", "math")

    def test_generate_response_error_handling(self):
        """AI応答エラーハンドリングのテスト"""
        with patch('app.ai.generate_chat_response') as mock_ai:
            mock_ai.side_effect = Exception("API Error")
            
            service = AIService()
            response = service.generate_response("テスト", "general")
            
            assert "申し訳ありません" in response
```

#### 3. ユーティリティテスト例

```python
# tests/unit/test_utils.py
import pytest
from app.utils.validators import validate_email, validate_password
from app.utils.encryption import encrypt_data, decrypt_data

class TestValidators:
    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name+tag@domain.co.jp", True),
        ("invalid-email", False),
        ("@domain.com", False),
        ("user@", False)
    ])
    def test_validate_email(self, email, expected):
        """メール形式バリデーションのテスト"""
        result = validate_email(email)
        assert result == expected

class TestEncryption:
    def test_encrypt_decrypt_cycle(self):
        """暗号化・復号化サイクルのテスト"""
        original_data = "機密データ123"
        encrypted = encrypt_data(original_data)
        decrypted = decrypt_data(encrypted)
        
        assert encrypted != original_data
        assert decrypted == original_data
```

### フィクスチャの活用

```python
# tests/conftest.py
import pytest
from app import create_app, db
from app.models import User, School, Class
from config import TestingConfig

@pytest.fixture
def app():
    """テスト用Flaskアプリ"""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()

@pytest.fixture
def sample_school(app):
    """サンプル学校データ"""
    school = School(name='テスト中学校', location='東京都')
    db.session.add(school)
    db.session.commit()
    return school

@pytest.fixture
def sample_user(app, sample_school):
    """サンプルユーザーデータ"""
    user = User(
        username='test_student',
        email='student@test.com',
        role='student',
        school_id=sample_school.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def authenticated_client(client, sample_user):
    """認証済みクライアント"""
    with client.session_transaction() as sess:
        sess['user_id'] = sample_user.id
        sess['_fresh'] = True
    return client
```

---

## 🔗 統合テスト

### APIエンドポイントテスト

```python
# tests/integration/test_auth_routes.py
import pytest
from app.models import User

class TestAuthRoutes:
    def test_login_success(self, client, sample_user):
        """ログイン成功のテスト"""
        response = client.post('/auth/login', data={
            'username': sample_user.username,
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'dashboard' in response.data

    def test_login_failure(self, client, sample_user):
        """ログイン失敗のテスト"""
        response = client.post('/auth/login', data={
            'username': sample_user.username,
            'password': 'wrong_password'
        })
        
        assert response.status_code == 200
        assert b'error' in response.data

class TestStudentRoutes:
    def test_student_dashboard_access(self, authenticated_client):
        """学生ダッシュボードアクセステスト"""
        response = authenticated_client.get('/student/dashboard')
        
        assert response.status_code == 200
        assert b'dashboard' in response.data

    def test_create_goal_api(self, authenticated_client):
        """目標作成APIテスト"""
        goal_data = {
            'title': 'テスト目標',
            'description': 'これはテスト用の目標です',
            'due_date': '2025-12-31'
        }
        
        response = authenticated_client.post('/api/goals', 
                                          json=goal_data,
                                          content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['goal']['title'] == 'テスト目標'
```

### データベース統合テスト

```python
# tests/integration/test_database.py
import pytest
from app.models import User, Goal, Todo
from sqlalchemy.exc import IntegrityError

class TestDatabaseIntegration:
    def test_user_goal_relationship(self, app, sample_user):
        """ユーザー・目標リレーションシップテスト"""
        with app.app_context():
            goal = Goal(
                student_id=sample_user.id,
                title='データベーステスト',
                description='リレーションシップのテスト'
            )
            db.session.add(goal)
            db.session.commit()
            
            # リレーションシップの確認
            user_goals = sample_user.goals.all()
            assert len(user_goals) == 1
            assert user_goals[0].title == 'データベーステスト'

    def test_cascade_delete(self, app, sample_user):
        """カスケード削除のテスト"""
        with app.app_context():
            # 関連データの作成
            goal = Goal(student_id=sample_user.id, title='テスト目標')
            todo = Todo(student_id=sample_user.id, title='テストTODO')
            
            db.session.add_all([goal, todo])
            db.session.commit()
            
            # ユーザー削除
            db.session.delete(sample_user)
            db.session.commit()
            
            # 関連データも削除されることを確認
            assert Goal.query.filter_by(student_id=sample_user.id).count() == 0
            assert Todo.query.filter_by(student_id=sample_user.id).count() == 0
```

---

## 🎭 E2Eテスト (End-to-End)

### Seleniumテスト設定

```python
# tests/e2e/conftest.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture(scope="session")
def driver():
    """Seleniumドライバー"""
    options = Options()
    options.add_argument("--headless")  # ヘッドレスモード
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

@pytest.fixture
def live_server(app):
    """ライブサーバー"""
    server = app.run(host='0.0.0.0', port=5555, threaded=True)
    yield 'http://localhost:5555'
```

### ユーザーフローテスト

```python
# tests/e2e/test_student_flow.py
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestStudentWorkflow:
    def test_complete_student_workflow(self, driver, live_server, sample_user):
        """完全な学生ワークフローのテスト"""
        # 1. ログイン
        driver.get(f"{live_server}/auth/login")
        
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        
        username_input.send_keys(sample_user.username)
        password_input.send_keys("password123")
        
        login_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        login_button.click()
        
        # ダッシュボードへのリダイレクトを確認
        WebDriverWait(driver, 10).until(
            EC.url_contains("/student/dashboard")
        )
        
        # 2. 目標作成
        driver.find_element(By.LINK_TEXT, "目標管理").click()
        driver.find_element(By.LINK_TEXT, "新規目標").click()
        
        title_input = driver.find_element(By.NAME, "title")
        title_input.send_keys("E2Eテスト目標")
        
        description_textarea = driver.find_element(By.NAME, "description")
        description_textarea.send_keys("これはE2Eテストで作成された目標です")
        
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        
        # 成功メッセージの確認
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        assert "目標が作成されました" in success_message.text
        
        # 3. TODO作成
        driver.find_element(By.LINK_TEXT, "TODO管理").click()
        driver.find_element(By.LINK_TEXT, "新規TODO").click()
        
        todo_title = driver.find_element(By.NAME, "title")
        todo_title.send_keys("E2EテストTODO")
        
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        
        # TODO一覧で作成されたTODOを確認
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "E2EテストTODO")
        )

class TestTeacherWorkflow:
    def test_curriculum_creation(self, driver, live_server, sample_teacher):
        """教師カリキュラム作成フローのテスト"""
        # ログイン
        driver.get(f"{live_server}/auth/login")
        
        # 教師としてログイン
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        
        username_input.send_keys(sample_teacher.username)
        password_input.send_keys("teacher_password")
        
        login_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        login_button.click()
        
        # カリキュラム管理に移動
        driver.find_element(By.LINK_TEXT, "カリキュラム管理").click()
        driver.find_element(By.LINK_TEXT, "新規作成").click()
        
        # カリキュラム情報入力
        name_input = driver.find_element(By.NAME, "name")
        name_input.send_keys("E2Eテストカリキュラム")
        
        subject_select = driver.find_element(By.NAME, "subject")
        subject_select.send_keys("数学")
        
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        
        # 作成成功の確認
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "カリキュラムが作成されました")
        )
```

---

## 📊 テスト実行とレポート

### 基本的なテスト実行

```bash
# 全テストの実行
python -m pytest

# 特定のテストファイルのみ
python -m pytest tests/unit/test_models.py

# 特定のテストクラスのみ
python -m pytest tests/unit/test_models.py::TestUserModel

# 特定のテストメソッドのみ
python -m pytest tests/unit/test_models.py::TestUserModel::test_create_user

# 詳細出力
python -m pytest -v

# 失敗時にデバッグ情報を表示
python -m pytest -vvv --tb=long
```

### カバレッジレポート

```bash
# カバレッジ付きテスト実行
python -m pytest --cov=app --cov-report=html --cov-report=term

# カバレッジレポートの確認
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# 特定のモジュールのみカバレッジ測定
python -m pytest --cov=app.models --cov=app.services
```

### 並列テスト実行

```bash
# pytestプラグインのインストール
pip install pytest-xdist

# 並列実行（CPUコア数分）
python -m pytest -n auto

# 指定した数で並列実行
python -m pytest -n 4
```

---

## 🚀 継続的インテグレーション (CI)

### GitHub Actions設定

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: quested_test
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock pytest-flask
    
    - name: Set up database
      run: |
        mysql -h127.0.0.1 -uroot -proot -e "GRANT ALL ON quested_test.* TO 'root'@'%';"
    
    - name: Run tests
      env:
        DATABASE_URL: mysql://root:root@127.0.0.1/quested_test
        FLASK_ENV: testing
      run: |
        python -m pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 🔧 テストのベストプラクティス

### 1. テストの原則

- **独立性**: 各テストは他のテストに依存しない
- **反復可能**: 何度実行しても同じ結果
- **高速**: ユニットテストは1秒以内に完了
- **明確**: テスト名で何をテストしているか分かる

### 2. テストデータ管理

```python
# Factory Boyを使用したテストデータ生成
import factory
from app.models import User, School

class SchoolFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = School
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker('company', locale='ja_JP')
    location = factory.Faker('address', locale='ja_JP')

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    full_name = factory.Faker('name', locale='ja_JP')
    school = factory.SubFactory(SchoolFactory)
```

### 3. モック活用

```python
# 外部サービスのモック
@patch('app.services.email_service.send_email')
def test_user_registration_sends_email(mock_send_email, client):
    """ユーザー登録時のメール送信テスト"""
    mock_send_email.return_value = True
    
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 201
    mock_send_email.assert_called_once()
```

### 4. テスト環境の分離

```python
# テスト用設定クラス
class TestingConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'mysql://test_user:password@localhost/quested_test'
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    OPENAI_API_KEY = 'test-api-key'  # テスト用ダミーキー
```

---

## 📈 パフォーマンステスト

### 基本的なパフォーマンステスト

```python
# tests/performance/test_load.py
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

class TestPerformance:
    def test_api_response_time(self, client):
        """API応答時間のテスト"""
        start_time = time.time()
        
        response = client.get('/api/goals')
        
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0  # 2秒以内

    def test_concurrent_requests(self, client):
        """同時リクエスト処理のテスト"""
        def make_request():
            return client.get('/api/dashboard')
        
        # 10個の同時リクエスト
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            
            for future in as_completed(futures):
                response = future.result()
                assert response.status_code == 200
```

---

## 🎯 テスト戦略のまとめ

### 1. 優先順位

1. **最優先**: 認証・認可、データ整合性
2. **高優先**: API機能、ビジネスロジック
3. **中優先**: UI機能、統合機能
4. **低優先**: 静的コンテンツ、管理機能

### 2. テスト実行タイミング

- **開発時**: ユニットテスト
- **コミット前**: ユニット + 統合テスト
- **プルリクエスト**: 全テスト
- **リリース前**: 全テスト + E2Eテスト

### 3. 品質指標

- **カバレッジ**: 90%以上
- **テスト成功率**: 100%
- **実行時間**: 5分以内（CI環境）
- **テストメンテナンス**: 月1回見直し

---

<div align="center">
  <p>
    品質の高いテストで、安全なQuestEd開発を！🧪✨
  </p>
  <p>
    <a href="#quested-テストガイド">トップに戻る ⬆️</a>
  </p>
</div>