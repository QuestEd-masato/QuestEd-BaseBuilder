# QuestEd - 探究型学習支援プラットフォーム

<div align="center">
  <h3>🎓 次世代の教育を支えるAI搭載学習管理システム</h3>
  <p>
    <a href="#機能">機能</a> •
    <a href="#インストール">インストール</a> •
    <a href="#使い方">使い方</a> •
    <a href="#ドキュメント">ドキュメント</a> •
    <a href="#ライセンス">ライセンス</a>
  </p>
</div>

---

## 📚 概要

QuestEdは、中学校・高等学校向けの探究型学習を支援する総合的な教育プラットフォームです。AI技術を活用して、生徒一人ひとりに最適化された学習体験を提供し、教師の指導をサポートします。

### 🌟 主な特徴

- **🤖 AI学習支援**: 各教科に特化したAIプロンプトによる個別指導
- **📊 進捗管理**: リアルタイムの学習進捗追跡と可視化
- **👥 多役割対応**: 管理者・教師・生徒の各役割に応じた機能
- **🏫 学校管理**: クラス編成、生徒管理、年度管理
- **📝 自動レポート**: AI生成の日次学習レポート
- **🔒 セキュリティ**: 多要素認証（MFA）、FERPA/COPPA準拠

## 🛠️ 技術スタック

- **バックエンド**: Flask 2.2.3 (Python 3.8+)
- **データベース**: MySQL 8.0
- **ORM**: SQLAlchemy 3.0.3
- **認証**: Flask-Login + 多要素認証 (pyotp)
- **フロントエンド**: Bootstrap 5 + jQuery
- **AI**: OpenAI API
- **キャッシュ**: Redis (オプション)
- **タスクキュー**: Celery (オプション)

## 🚀 クイックスタート

### 必要条件

- Python 3.8以上
- MySQL 8.0以上
- Git

### インストール

1. **リポジトリのクローン**
```bash
git clone https://github.com/yourusername/quested.git
cd quested
```

2. **仮想環境の作成と有効化**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

3. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

4. **環境変数の設定**
```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

5. **データベースの初期化**
```bash
# MySQLデータベースを作成
mysql -u root -p -e "CREATE DATABASE quested CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# マイグレーションを実行
flask db upgrade
```

6. **アプリケーションの起動**
```bash
flask run
```

アプリケーションは `http://localhost:5000` でアクセスできます。

## 📖 ドキュメント

### 📋 技術ドキュメント

- **[技術仕様書](TECHNICAL_SPECIFICATION.md)** - システムアーキテクチャと開発ガイド
- **[CLAUDE.md](CLAUDE.md)** - 開発者向けプロジェクトガイドライン
- **[プロジェクト履歴](PROJECT_HISTORY.md)** - 開発履歴と改善記録

### 📚 開発・運用ガイド

- **[データベース設計](DATABASE.md)** - データベーススキーマと設計思想
- **[段階的改善計画](FUNDAMENTAL_REFORM_PLAN.md)** - システム改善ロードマップ

### 🚀 アーキテクチャ改善状況

- **技術的負債レベル**: Grade D+ → Grade B+ (大幅改善達成)
- **Phase1-8B完了**: 神クラス・神関数解消、Service Layer Architecture確立
- **システム状況**: ✅ 正常動作確認済み（仮想環境）

## 🎯 使い方

### 初回セットアップ

1. 管理者アカウントでログイン
2. 学校情報を登録
3. 教師アカウントを作成
4. クラスを作成し、生徒を登録

### 主要機能

#### 管理者向け
- 学校・年度管理
- ユーザー一括登録
- システム全体の統計閲覧

#### 教師向け
- カリキュラム作成・管理
- 生徒の進捗モニタリング
- AI支援による評価レポート生成
- 探究テーマの承認

#### 生徒向け
- 探究テーマの選択・作成
- 学習活動の記録
- AI チューターとの対話
- 目標・TODO管理

## 🗂️ プロジェクト構造

```
QuestEd/
├── app/                    # アプリケーションコード
│   ├── admin/             # 管理者機能
│   ├── ai/                # AI統合機能 
│   ├── api/               # RESTful API
│   ├── auth/              # 認証・認可（MFA対応）
│   ├── models/            # データベースモデル
│   ├── modules/           # モジュラーシステム
│   │   ├── lesson_system/ # レッスン管理システム
│   │   └── ranking_system/# ランキングシステム
│   ├── services/          # Service Layer Architecture
│   │   ├── ai/           # AI専門サービス群
│   │   ├── curriculum/   # カリキュラム専門サービス群
│   │   ├── dashboard/    # ダッシュボード専門サービス群
│   │   ├── student_dashboard/ # 学生ダッシュボード専門サービス群
│   │   ├── sync/         # 同期専門サービス群
│   │   ├── task/         # タスク専門サービス群
│   │   ├── unit/         # 単元専門サービス群
│   │   └── weakness/     # 弱点分析専門サービス群
│   ├── student/          # 生徒機能
│   ├── teacher/          # 教師機能
│   └── utils/            # ユーティリティ
├── migrations/           # データベースマイグレーション
│   └── manual_sql/      # 手動SQLファイル（段階的統合予定）
├── scripts/             # 運用スクリプト
├── static/              # 静的ファイル
├── templates/           # HTMLテンプレート
├── tests/               # テストコード（整理済み）
├── requirements.txt     # Python依存関係
├── config.py           # 設定ファイル
└── app.py              # アプリケーションエントリーポイント
```

## 🔒 セキュリティ機能

- **認証**: セッションベース認証 + JWT (API)
- **多要素認証**: TOTP方式のMFA
- **暗号化**: Fernet (AES-128) によるデータ暗号化
- **アクセス制御**: ロールベース + リソース所有権チェック
- **セキュリティヘッダー**: XSS、CSRF、クリックジャッキング対策
- **監査ログ**: 全ての重要操作を記録

## 📊 データベース

- **テーブル数**: 69
- **主要エンティティ**: users, classes, curriculum_units, activity_logs, ai_recommendations
- **詳細**: [DATABASE.md](DATABASE.md) を参照

## 🌐 API

RESTful APIを提供しており、外部システムとの連携が可能です。

- **認証**: Bearer Token
- **形式**: JSON
- **詳細**: [API仕様書](docs/api/API_SPECIFICATION.md) を参照

## 🧪 テスト

```bash
# 全テストの実行
python -m pytest

# カバレッジレポート付き
python -m pytest --cov=app --cov-report=html

# 特定のテストのみ
python -m pytest tests/unit/test_models.py
```

## 🚢 デプロイメント

本番環境へのデプロイメント手順は [TECHNICAL_SPECIFICATION.md](TECHNICAL_SPECIFICATION.md) を参照してください。

### 推奨構成
- **Webサーバー**: Nginx + Gunicorn
- **データベース**: MySQL 8.0 (Amazon RDS推奨)
- **アプリケーションサーバー**: EC2 t3.medium以上
- **ロードバランサー**: ALB (高可用性構成の場合)

## 📝 ドキュメント

- [技術仕様書](TECHNICAL_SPECIFICATION.md) - 包括的システムアーキテクチャ・開発ガイド
- [データベース設計](DATABASE.md) - データベーススキーマと設計思想
- [CLAUDE.md](CLAUDE.md) - 開発者向けプロジェクトガイドライン
- [プロジェクト履歴](PROJECT_HISTORY.md) - Phase1-8B完了記録

## 🤝 貢献

貢献を歓迎します！以下の手順でご参加ください：

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

詳細は [CLAUDE.md](CLAUDE.md) の開発ガイドラインをご覧ください。

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) の下でライセンスされています。

## 👥 開発チーム

- **プロジェクトリード**: [Your Name]
- **バックエンド開発**: [Backend Team]
- **フロントエンド開発**: [Frontend Team]
- **デザイン**: [Design Team]

## 📞 サポート

- **技術仕様**: [TECHNICAL_SPECIFICATION.md](TECHNICAL_SPECIFICATION.md)
- **開発ガイドライン**: [CLAUDE.md](CLAUDE.md)
- **データベース**: [DATABASE.md](DATABASE.md)

---

<div align="center">
  <p>
    Made with ❤️ by QuestEd Development Team
  </p>
  <p>
    <a href="#quested---探究型学習支援プラットフォーム">Back to top ⬆️</a>
  </p>
</div>