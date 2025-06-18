-- カリキュラム機能 v2 - 新テーブル作成
-- 実行日: 2025-01-15

-- 1. カリキュラム項目テーブル
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

-- 確認用クエリ
SELECT 'curriculum_items table created' as status, COUNT(*) as count FROM curriculum_items;
SELECT 'curriculum_category_problems table created' as status, COUNT(*) as count FROM curriculum_category_problems;