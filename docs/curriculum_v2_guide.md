# QuestEd カリキュラム機能 v2 ガイド

## 🎯 概要

カリキュラム機能 v2 は、従来の複雑なJSON構造を廃止し、シンプルなテーブル形式でカリキュラムを管理する新しいシステムです。

### 主要改善点

1. **シンプルなデータ構造** - Excelライクなテーブル形式
2. **CSVとの完全互換** - インポート/エクスポートが簡単
3. **BaseBuilder連携** - カテゴリベースの問題提案
4. **モダンUI** - 直感的な編集インターフェース
5. **高速化** - SQLクエリによる効率的なデータ処理

## 🗄️ データベース構造

### curriculum_items テーブル
```sql
CREATE TABLE curriculum_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    curriculum_id INT NOT NULL,
    phase VARCHAR(100),              -- フェーズ（準備期、探究前半など）
    week VARCHAR(50),                -- 週（第1週、第2-4週など）
    hours INT DEFAULT 0,             -- 時間数
    category VARCHAR(200),           -- カテゴリ（BaseBuilder連携用）
    activity TEXT,                   -- 活動内容
    teacher_support TEXT,            -- 教師のサポート
    evaluation_method TEXT,          -- 評価方法
    order_index INT DEFAULT 0,       -- 表示順序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### curriculum_category_problems テーブル
```sql
CREATE TABLE curriculum_category_problems (
    id INT PRIMARY KEY AUTO_INCREMENT,
    curriculum_item_id INT NOT NULL,
    problem_category_id INT,         -- BaseBuilderのカテゴリID
    category_name VARCHAR(200),      -- カテゴリ名
    min_score INT DEFAULT 0,         -- 推奨最低正答率
    problem_count INT DEFAULT 5      -- 出題数
);
```

## 🚀 使用方法

### 1. 新システムへの移行

```bash
# 移行スクリプト実行
python migrate_curriculum_v2.py
```

### 2. 新しいカリキュラム作成

1. 通常通りカリキュラムを作成
2. 編集画面で「新形式で編集」を選択
3. テーブル形式で項目を追加

### 3. CSV操作

#### エクスポート
```
フェーズ,週,時間数,カテゴリ,活動内容,教師のサポート,評価方法
準備期,第1週,2,オリエンテーション,QuestEdの使い方説明,全体説明・個別サポート,参加態度
```

#### インポート
- 同じ形式のCSVファイルを用意
- 編集画面でアップロード
- 自動的にテーブル項目に変換

### 4. BaseBuilder連携

カテゴリ名を設定すると：
- 関連問題が自動検索
- 学生の正答率に基づく復習問題生成
- 練習問題への直接リンク

## 🔧 API仕様

### 新しいエンドポイント

```
GET  /curriculum/{id}/view-v2      # 新形式での表示
GET  /curriculum/{id}/edit-v2      # 新形式での編集
POST /curriculum/{id}/edit-v2      # 項目の保存
POST /curriculum/{id}/import-v2    # CSVインポート
GET  /curriculum/{id}/export-v2    # CSVエクスポート
POST /curriculum/{id}/migrate      # 旧形式からの移行
GET  /api/curriculum/problems      # 関連問題取得
```

### リクエスト例

#### カリキュラム項目保存
```json
{
  "title": "探究学習カリキュラム",
  "description": "総合探究の時間",
  "items": [
    {
      "phase": "準備期",
      "week": "第1週",
      "hours": 2,
      "category": "オリエンテーション",
      "activity": "QuestEdの使い方説明",
      "teacher_support": "全体説明、個別サポート",
      "evaluation_method": "参加態度"
    }
  ]
}
```

#### 関連問題取得
```javascript
fetch('/api/curriculum/problems?category=プログラミング基礎&item_id=123')
```

## 🎨 UIコンポーネント

### 表示画面の特徴

- **統計情報** - 項目数、総時間数、フェーズ数、カテゴリ数
- **テーブル表示** - フェーズごとにグループ化
- **カテゴリバッジ** - クリックで関連問題表示
- **問題連携** - BaseBuilderへの直接リンク

### 編集画面の特徴

- **リアルタイム編集** - Excelライクな操作感
- **CSV操作** - ドラッグ&ドロップでインポート
- **自動保存** - 下書き保存機能
- **データ検証** - 入力値の自動チェック

## 🔄 移行ガイド

### 既存カリキュラムの移行

1. **自動移行**
   ```bash
   python migrate_curriculum_v2.py
   ```

2. **手動移行**
   - カリキュラム表示画面で「新形式に移行」ボタン
   - JSONデータを自動解析してテーブル形式に変換

3. **移行確認**
   - 元データはバックアップとして保持
   - 移行後は format='table' に変更

### 移行時の注意点

- **データ構造の違い**
  - JSONの複雑な入れ子構造 → フラットなテーブル
  - セクション/レッスン → フェーズ/週の概念

- **データの正規化**
  - 重複する情報の統合
  - 空フィールドの適切な処理

## 🧪 テスト手順

### 1. 基本機能テスト

```bash
# 1. 移行スクリプト実行
python migrate_curriculum_v2.py

# 2. サンプルカリキュラムの確認
# ブラウザで /curriculum/[sample_id]/view-v2 にアクセス

# 3. 編集機能テスト
# ブラウザで /curriculum/[sample_id]/edit-v2 にアクセス
```

### 2. CSV機能テスト

1. **エクスポート**
   - 編集画面で「CSVダウンロード」
   - Excelで開いて文字化けがないかチェック

2. **インポート**
   - サンプルCSVを編集
   - 編集画面でアップロード
   - データが正しく反映されるかチェック

### 3. BaseBuilder連携テスト

1. **関連問題検索**
   - カテゴリバッジをクリック
   - 関連問題が表示されるかチェック

2. **復習問題生成**
   - 学生アカウントでログイン
   - 低正答率問題が優先表示されるかチェック

## 🚨 トラブルシューティング

### よくある問題

1. **テーブルが作成されない**
   ```bash
   # データベース権限を確認
   SHOW GRANTS FOR CURRENT_USER;
   
   # 手動でテーブル作成
   SOURCE migrations/create_curriculum_v2_tables.sql;
   ```

2. **CSV文字化け**
   - UTF-8 BOM付きで出力されているか確認
   - Excelの「データ」>「テキストファイル」でインポート

3. **BaseBuilder連携不具合**
   ```sql
   -- problem_categoriesテーブルの確認
   SELECT COUNT(*) FROM problem_categories;
   
   -- basic_knowledge_itemsとの関連確認
   SELECT pc.name, COUNT(bki.id) as item_count 
   FROM problem_categories pc 
   LEFT JOIN basic_knowledge_items bki ON pc.id = bki.category_id 
   GROUP BY pc.id;
   ```

4. **パフォーマンス問題**
   ```sql
   -- インデックスの確認
   SHOW INDEX FROM curriculum_items;
   SHOW INDEX FROM curriculum_category_problems;
   
   -- 実行計画の確認
   EXPLAIN SELECT * FROM curriculum_items WHERE curriculum_id = 1;
   ```

## 📊 パフォーマンス最適化

### 推奨設定

1. **データベース**
   ```sql
   -- インデックス最適化
   CREATE INDEX idx_curriculum_items_lookup ON curriculum_items(curriculum_id, order_index);
   CREATE INDEX idx_category_search ON curriculum_items(category);
   ```

2. **キャッシュ設定**
   ```python
   # Redis設定（推奨）
   REDIS_URL = "redis://localhost:6379/0"
   CACHE_TYPE = "redis"
   ```

## 🎁 サンプルデータ

### サンプルCSV
```csv
フェーズ,週,時間数,カテゴリ,活動内容,教師のサポート,評価方法
準備期,第1週,2,オリエンテーション,QuestEdの使い方説明、探究学習の概要,全体説明、質疑応答、個別サポート,参加態度、理解度確認
準備期,第2週,2,テーマ設定,興味関心の探索、初期テーマ設定,個別面談、テーマ設定支援,テーマ設定シート
探究前半,第3-4週,4,情報収集,文献調査、Web検索、基礎知識学習,調査方法指導、信頼性確認,調査記録、参考文献リスト
探究後半,第5-6週,4,分析・考察,収集データの分析、仮説検証,分析手法指導、論理的思考支援,分析レポート、考察の深さ
まとめ期,第7週,2,発表準備,プレゼンテーション資料作成,資料作成指導、発表練習,資料の完成度、構成
まとめ期,第8週,2,発表会,最終発表、相互評価,発表進行、評価基準説明,発表内容、質疑応答、相互評価
```

## 📝 今後の開発予定

1. **v2.1** - AIによるカリキュラム生成
2. **v2.2** - 学習進捗トラッキング
3. **v2.3** - 協働編集機能
4. **v2.4** - 評価ルーブリック連携

---

**Author**: QuestEd Development Team  
**Version**: 2.0.0  
**Last Updated**: 2025-01-15