# Blueprint命名規則

## 概要
QuestEdシステムでのFlask Blueprint命名規則とベストプラクティス

## 命名規則

### 基本原則
1. **一意性**: 全システム内で一意の名前
2. **説明性**: 機能が分かる名前
3. **階層性**: モジュール構造を反映

### 命名パターン

#### アプリケーション本体 (app/)
- `admin_panel` - 管理機能
- `auth` - 認証機能  
- `teacher` - 教師機能
- `student` - 学生機能
- `api` - API機能
- `realtime` - リアルタイム機能

#### API分割モジュール (app/api/)
- `api_*` または機能名 - 機能別API
- 例: `chat_ai`, `unit_management`, `rankings`

#### 教師・学生サブモジュール (app/teacher/modules/, app/student/modules/)
- `{role}_{function}` パターン
- 例: `teacher_dashboard`, `student_activities`

#### BaseBuilderモジュール (basebuilder/)
- `basebuilder_*` プレフィックス
- 例: `basebuilder_admin`, `basebuilder_module`
- または機能名のみ: `categories`, `problems`

#### Coreモジュール (core/)
- 機能名のみ: `academic`, `enrollment`, `school`

## 重複防止チェック

### 自動チェックスクリプト
```bash
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

# 重複報告
for name, files in blueprints.items():
    if len(files) > 1:
        print(f'DUPLICATE: {name} in {files}')
"
```

### CI/CDでの自動チェック
```yaml
# .github/workflows/blueprint-check.yml
- name: Check Blueprint Duplicates
  run: |
    python3 scripts/check_blueprints.py
```

## 修正履歴

### 2025-06-28: 重複問題解決
- `basebuilder/routes/admin.py`: 'admin' → 'basebuilder_admin'
- レガシーファイル削除: `app/api/__init___legacy.py.bak`
- レガシーファイル削除: `basebuilder/routes_legacy.py.bak`

### 結果
- Blueprint重複: 2個 → 0個
- 登録Blueprint数: 36個 (全て一意)
- システム起動: ✅ 正常

## 今後の注意点

1. **新しいBlueprint作成時**: 必ず既存名との重複をチェック
2. **リファクタリング時**: Blueprint名変更は影響範囲を確認
3. **レガシーファイル**: .bak拡張子をつけて無効化
4. **url_for()**: Blueprint名変更時はテンプレートも更新

## トラブルシューティング

### ValueError: The name 'xxx' is already registered
1. 重複チェックスクリプトを実行
2. 重複するBlueprintの一方を名前変更
3. レガシーファイルが残っていないか確認

### ImportError
1. Blueprint定義ファイルの構文チェック
2. インポートパスの確認
3. 循環インポートの確認