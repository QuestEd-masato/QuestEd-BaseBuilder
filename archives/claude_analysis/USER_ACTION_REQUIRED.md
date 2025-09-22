# ユーザー様による直接対応が必要なセキュリティ項目

**作成日**: 2025-08-23  
**緊急度**: 🔴 **最高**

## なぜユーザー様が直接行う必要があるのか

### セキュリティ上の理由
- **認証情報**: GitHubトークンやAWSパスワードは個人の認証情報
- **権限**: Claude Codeには外部サービスの管理権限がない
- **責任**: セキュリティ設定の変更は所有者が直接実施すべき

### 技術的な理由
- **GitHub**: Personal Access Tokenは所有者のみが無効化可能
- **AWS**: RDSパスワード変更にはAWSコンソールアクセスが必要
- **アクセス制限**: Claude Codeは読み取り専用操作のみ可能

## 🚨 ユーザー様が実施すべき緊急対応

### 1. GitHubトークンの無効化と再生成

#### Step 1: 現在のトークンを無効化
```
1. GitHub.com にログイン
2. 右上のプロフィール画像をクリック
3. Settings → Developer settings → Personal access tokens → Tokens (classic)
4. トークン一覧から「[REDACTED_GITHUB_TOKEN]」を探す
5. 「Delete」をクリックして削除
```

#### Step 2: 新しいトークンを生成
```
1. 「Generate new token (classic)」をクリック
2. Note: "QuestEd Development" など適切な名前を入力
3. Expiration: 適切な有効期限を設定
4. Scopes: repo（必要最小限の権限）
5. 「Generate token」をクリック
6. 生成されたトークンをコピー（一度しか表示されません）
```

#### Step 3: ローカルのGit設定を更新
```bash
# 現在のディレクトリで実行
cd /home/masat/claude-projects/QuestEd
git remote set-url origin https://[新しいトークン]@github.com/QuestEd-masato/QuestEd-BaseBuilder.git
```

### 2. RDSパスワードの変更

#### Step 1: AWSコンソールにアクセス
```
1. AWS Management Console にログイン
2. RDS サービスに移動
3. 「Databases」を選択
4. 「database-1」インスタンスを選択
```

#### Step 2: パスワード変更
```
1. 「Modify」ボタンをクリック
2. 「Database authentication」セクションを探す
3. 「Master password」で「Auto generate a password」または手動入力
4. 新しいパスワードを設定（例: QuestEd-NewPass-2025）
5. 「Continue」→「Modify DB instance」をクリック
```

#### Step 3: アプリケーション設定の更新
```
EC2インスタンス (13.113.164.85) にSSH接続して:
1. /var/www/quested/QuestEd/.env ファイルを編集
2. DB_PASSWORD=新しいパスワード に変更
3. sudo systemctl restart quested でサービス再起動
```

### 3. 追加のセキュリティ設定（推奨）

#### EC2セキュリティグループの確認
```
1. EC2 コンソールに移動
2. Security Groups を確認
3. SSH (port 22) の接続元を特定のIPに制限
4. HTTP/HTTPS以外の不要なポートを閉鎖
```

#### RDSセキュリティ設定の確認
```
1. RDS コンソールでセキュリティグループを確認
2. MySQL/Aurora (port 3306) の接続元をEC2のセキュリティグループのみに制限
3. パブリックアクセスが無効になっていることを確認
```

## ⏰ 実施のタイミング

### 最優先（可能であれば今すぐ）
1. **GitHubトークン無効化**: 5分程度で完了可能
2. **新しいトークン生成と設定**: 10分程度

### 高優先（本日中）
3. **RDSパスワード変更**: 15-20分程度
4. **アプリケーション設定更新**: 5-10分程度

### 中優先（今週中）
5. **セキュリティ設定の見直し**: 30分程度

## 🤝 Claude Codeができる支援

### 実施後にClaude Codeが対応できること
1. **新しい認証情報での.env.questedファイル作成**
2. **CLAUDE.mdの機密情報除去とコミット**
3. **接続テストや動作確認の支援**
4. **設定ファイルの更新支援**

### 実施中にClaude Codeができること
1. **手順の詳細な説明**
2. **設定ファイルのテンプレート提供**
3. **トラブルシューティング**

## 📋 完了チェックリスト

- [ ] GitHubトークン削除完了
- [ ] 新しいトークン生成完了
- [ ] ローカルGit設定更新完了
- [ ] RDSパスワード変更完了
- [ ] EC2の.env設定更新完了
- [ ] アプリケーション再起動完了
- [ ] 動作確認完了

これらの対応完了後、Claude CodeでCLAUDE.mdの機密情報除去作業を進めさせていただきます。

## ❓ 不明な点がある場合

各手順で不明な点があれば、Claude Codeに質問してください。画面の案内や具体的なコマンド例など、詳細にサポートいたします。