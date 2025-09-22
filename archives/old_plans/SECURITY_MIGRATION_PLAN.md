# QuestEd セキュリティ情報分離計画

**作成日**: 2025-08-23
**目的**: CLAUDE.mdから機密情報を分離し、GitHubへの流出を防止

## 📋 実施計画

### Phase 1: 環境設定ファイルの作成
**ファイル名**: `.env.quested`

**含める情報**:
```bash
# EC2接続情報
QUESTED_EC2_HOST=13.113.164.85
QUESTED_EC2_USER=ec2-user
QUESTED_EC2_KEY_PATH=~/.ssh/quested-key.pem

# RDS接続情報
QUESTED_RDS_HOST=database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com
QUESTED_DB_NAME=quested
QUESTED_DB_USER=QuestEd
QUESTED_DB_PASSWORD=QuestEd-03012025MySQL

# ローカルDB接続情報
QUESTED_LOCAL_DB_HOST=localhost
QUESTED_LOCAL_DB_PORT=3306
QUESTED_LOCAL_DB_USER=QuestEd
QUESTED_LOCAL_DB_PASSWORD=QuestEd-03012025MySQL
```

### Phase 2: CLAUDE.md修正箇所

#### 修正前の例:
```markdown
- **サーバー**: EC2 13.113.164.85 (Amazon Linux 2023)
- **データベース**: RDS database-1.cdk0iio0s90g.ap-northeast-1.rds.amazonaws.com
```

#### 修正後の例:
```markdown
- **サーバー**: EC2 [.env.quested: QUESTED_EC2_HOST] (Amazon Linux 2023)
- **データベース**: RDS [.env.quested: QUESTED_RDS_HOST]
```

### Phase 3: .gitignore更新

追加する内容:
```
# QuestEd機密情報
.env.quested
```

### Phase 4: git remoteの修正

現在の問題:
```
https://[REDACTED_GITHUB_TOKEN]@github.com/QuestEd-masato/QuestEd-BaseBuilder.git
```

修正後:
```
https://github.com/QuestEd-masato/QuestEd-BaseBuilder.git
```
（トークンは別途管理）

## 📊 変更影響範囲

### CLAUDE.md内の修正必要箇所:
1. **7行目**: 13.113.164.85のEC2インスタンス
2. **14行目**: 13.113.164.85 EC2完全復旧
3. **19-23行目**: 本番環境情報セクション
4. **59-60行目**: SSH接続情報
5. **290-291行目**: 本番環境DB接続
6. **299-300行目**: ローカルDB接続
7. **1013行目**: インフラ確立情報
8. **1019-1020行目**: サーバー・データベース情報

## 🔒 セキュリティ向上効果

1. **機密情報の分離**: CLAUDE.mdからすべての接続情報を除去
2. **Git追跡の防止**: .env.questedは.gitignoreで除外
3. **参照形式**: 開発者は.env.questedファイルを別途作成
4. **トークン管理**: GitHubトークンをURLから除去

## ⚠️ 注意事項

1. **.env.questedファイル**:
   - 各開発者がローカルに作成
   - 絶対にコミットしない
   - テンプレートは.env.quested.exampleとして提供可能

2. **既存の履歴**:
   - 既にGitHubに公開済みの情報は履歴に残る
   - 完全削除にはgit filter-branchが必要（別途検討）

3. **運用への影響**:
   - 新規開発者は.env.questedファイルの作成が必要
   - ドキュメントの可読性は若干低下するが、セキュリティ向上

## 実施手順

1. ✅ この計画書の作成と確認
2. ⏳ .env.questedファイルの作成
3. ⏳ CLAUDE.mdの機密情報を参照形式に変更
4. ⏳ .gitignoreに.env.questedを追加
5. ⏳ git remote URLからトークンを除去
6. ⏳ 変更内容の確認とコミット

この計画で問題ないか確認してから実施します。