-- QuestEd カリキュラム機能v2 初期化SQL
-- カリキュラムID=7の表示・編集統合のためのテーブル作成とデータ初期化

-- 1. curriculum_itemsテーブルの作成
CREATE TABLE IF NOT EXISTS curriculum_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    curriculum_id INT NOT NULL,
    phase VARCHAR(100) DEFAULT '',           -- フェーズ（準備期、探究前半など）
    week VARCHAR(50) DEFAULT '',             -- 週（第1週、第2-4週など）
    hours INT DEFAULT 0,                     -- 時間数
    category VARCHAR(200) DEFAULT '',        -- カテゴリ（BaseBuilder連携用）
    activity TEXT DEFAULT '',                -- 活動内容
    teacher_support TEXT DEFAULT '',         -- 教師のサポート
    evaluation_method TEXT DEFAULT '',       -- 評価方法
    order_index INT DEFAULT 0,              -- 表示順序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(id) ON DELETE CASCADE,
    INDEX idx_curriculum_order (curriculum_id, order_index),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. BaseBuilder問題カテゴリとの連携テーブル
CREATE TABLE IF NOT EXISTS curriculum_category_problems (
    id INT PRIMARY KEY AUTO_INCREMENT,
    curriculum_item_id INT NOT NULL,
    problem_category_id INT,              -- problem_categoriesテーブルのID
    category_name VARCHAR(200) DEFAULT '',-- カテゴリ名（直接指定）
    min_score INT DEFAULT 0,              -- 推奨最低正答率
    problem_count INT DEFAULT 5,          -- 出題数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (curriculum_item_id) REFERENCES curriculum_items(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_category_id) REFERENCES problem_categories(id) ON DELETE SET NULL,
    INDEX idx_curriculum_item (curriculum_item_id),
    INDEX idx_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. curriculumsテーブルにフォーマット識別フィールドを追加
ALTER TABLE curriculums 
ADD COLUMN IF NOT EXISTS format VARCHAR(20) DEFAULT 'json'
COMMENT 'データ形式: json(レガシー) | table(新形式)';

-- 4. インデックスの追加
CREATE INDEX IF NOT EXISTS idx_curriculum_format ON curriculums(format);
CREATE INDEX IF NOT EXISTS idx_curriculum_teacher ON curriculums(teacher_id);
CREATE INDEX IF NOT EXISTS idx_curriculum_class ON curriculums(class_id);

-- 5. カリキュラムID=7の初期データ作成（既存データがない場合のみ）
INSERT IGNORE INTO curriculum_items 
(curriculum_id, phase, week, hours, category, activity, teacher_support, evaluation_method, order_index)
VALUES 
(7, '準備期', '第1週', 2, '基礎知識', '探究活動の基礎概念の理解', '概念説明と事例紹介', '理解度確認テスト', 1),
(7, '準備期', '第2週', 2, '情報収集', '情報収集手法の学習', '検索技術の指導', '情報収集レポート', 2),
(7, '探究前半', '第3-4週', 4, '問題発見', 'テーマ設定と問題の明確化', '個別指導とテーマ調整', '問題設定シート', 3),
(7, '探究前半', '第5-8週', 8, '調査・実験', '仮説設定と調査・実験の実施', '実験方法の指導と安全確保', '実験ノートの評価', 4),
(7, '探究後半', '第9-12週', 8, 'データ分析', 'データ分析と考察', '分析手法の指導', '分析レポート', 5),
(7, '探究後半', '第13-14週', 4, 'まとめ', '結論の整理と発表準備', 'プレゼンテーション指導', '発表練習の評価', 6),
(7, '発表期', '第15週', 2, 'プレゼンテーション', '研究成果の発表', '発表進行と質疑応答支援', '発表評価とピア評価', 7);

-- 6. カリキュラムID=7のフォーマットを'table'に更新
UPDATE curriculums 
SET format = 'table', updated_at = CURRENT_TIMESTAMP 
WHERE id = 7;

-- 7. 確認用クエリ
SELECT 'Tables created successfully' as status;
SELECT curriculum_id, COUNT(*) as item_count 
FROM curriculum_items 
WHERE curriculum_id = 7 
GROUP BY curriculum_id;

SELECT id, title, format 
FROM curriculums 
WHERE id = 7;