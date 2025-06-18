#!/usr/bin/env python3
"""
カリキュラム機能 v2 データベース移行スクリプト
新しいテーブルを作成し、既存データの移行を行う

実行方法:
python migrate_curriculum_v2.py

Author: QuestEd Development Team
Created: 2025-01-15
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_tables():
    """新しいテーブルを作成"""
    try:
        logger.info("Creating curriculum_items table...")
        
        # curriculum_items テーブル作成
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS curriculum_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                curriculum_id INT NOT NULL,
                phase VARCHAR(100) DEFAULT '',
                week VARCHAR(50) DEFAULT '',
                hours INT DEFAULT 0,
                category VARCHAR(200) DEFAULT '',
                activity TEXT DEFAULT '',
                teacher_support TEXT DEFAULT '',
                evaluation_method TEXT DEFAULT '',
                order_index INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (curriculum_id) REFERENCES curriculums(id) ON DELETE CASCADE,
                INDEX idx_curriculum_order (curriculum_id, order_index),
                INDEX idx_category (category)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        logger.info("Creating curriculum_category_problems table...")
        
        # curriculum_category_problems テーブル作成
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS curriculum_category_problems (
                id INT PRIMARY KEY AUTO_INCREMENT,
                curriculum_item_id INT NOT NULL,
                problem_category_id INT,
                category_name VARCHAR(200) DEFAULT '',
                min_score INT DEFAULT 0,
                problem_count INT DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (curriculum_item_id) REFERENCES curriculum_items(id) ON DELETE CASCADE,
                FOREIGN KEY (problem_category_id) REFERENCES problem_categories(id) ON DELETE SET NULL,
                INDEX idx_curriculum_item (curriculum_item_id),
                INDEX idx_category_name (category_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        logger.info("Adding format column to curriculums table...")
        
        # curriculums テーブルにフォーマット列を追加
        try:
            db.session.execute(text("""
                ALTER TABLE curriculums 
                ADD COLUMN IF NOT EXISTS format VARCHAR(20) DEFAULT 'json'
                COMMENT 'データ形式: json(レガシー) | table(新形式)'
            """))
        except Exception as e:
            if "Duplicate column name" not in str(e):
                raise e
            logger.info("Format column already exists")
        
        # インデックス追加
        try:
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_curriculum_format ON curriculums(format)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_curriculum_teacher ON curriculums(teacher_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_curriculum_class ON curriculums(class_id)"))
        except Exception as e:
            logger.warning(f"Index creation warning: {str(e)}")
        
        db.session.commit()
        logger.info("Database tables created successfully!")
        
        # 確認
        result = db.session.execute(text("SELECT COUNT(*) as count FROM curriculum_items"))
        count = result.scalar()
        logger.info(f"curriculum_items table: {count} records")
        
        result = db.session.execute(text("SELECT COUNT(*) as count FROM curriculum_category_problems"))
        count = result.scalar()
        logger.info(f"curriculum_category_problems table: {count} records")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        return False

def migrate_sample_data():
    """サンプルデータの移行"""
    try:
        from app.models import Curriculum
        from app.services.curriculum_service_v2 import CurriculumServiceV2
        
        logger.info("Migrating sample data...")
        
        # JSONフォーマットのカリキュラムを取得
        json_curriculums = db.session.execute(text("""
            SELECT id, title, content FROM curriculums 
            WHERE format = 'json' AND content IS NOT NULL AND content != ''
            LIMIT 5
        """)).fetchall()
        
        migrated_count = 0
        for curriculum in json_curriculums:
            try:
                success, message = CurriculumServiceV2.migrate_from_json(curriculum.id)
                if success:
                    migrated_count += 1
                    logger.info(f"Migrated curriculum {curriculum.id}: {curriculum.title}")
                else:
                    logger.warning(f"Failed to migrate curriculum {curriculum.id}: {message}")
            except Exception as e:
                logger.error(f"Error migrating curriculum {curriculum.id}: {str(e)}")
        
        logger.info(f"Successfully migrated {migrated_count} curriculums to v2 format")
        return True
        
    except Exception as e:
        logger.error(f"Error during sample data migration: {str(e)}")
        return False

def create_sample_curriculum():
    """サンプルカリキュラムの作成"""
    try:
        from app.models import Curriculum, Class, User
        from app.services.curriculum_service_v2 import CurriculumServiceV2
        
        logger.info("Creating sample curriculum...")
        
        # 最初の教師とクラスを取得
        teacher = db.session.execute(text("""
            SELECT id FROM users WHERE role = 'teacher' LIMIT 1
        """)).first()
        
        class_obj = db.session.execute(text("""
            SELECT id FROM classes LIMIT 1
        """)).first()
        
        if not teacher or not class_obj:
            logger.warning("No teacher or class found for sample data creation")
            return False
        
        # サンプルカリキュラムを作成
        sample_curriculum = Curriculum(
            title="QuestEd カリキュラム v2 サンプル",
            description="新しいテーブル形式でのサンプルカリキュラムです",
            class_id=class_obj.id,
            teacher_id=teacher.id,
            format='table'
        )
        
        db.session.add(sample_curriculum)
        db.session.flush()  # IDを取得
        
        # サンプル項目を追加
        sample_items = [
            {
                'phase': '準備期',
                'week': '第1週',
                'hours': 2,
                'category': 'オリエンテーション',
                'activity': 'QuestEdの使い方説明、探究学習の概要',
                'teacher_support': '全体説明、質疑応答、個別サポート',
                'evaluation_method': '参加態度、理解度確認'
            },
            {
                'phase': '準備期',
                'week': '第2週',
                'hours': 2,
                'category': 'テーマ設定',
                'activity': '興味関心の探索、初期テーマ設定',
                'teacher_support': '個別面談、テーマ設定支援',
                'evaluation_method': 'テーマ設定シート'
            },
            {
                'phase': '探究前半',
                'week': '第3-4週',
                'hours': 4,
                'category': '情報収集',
                'activity': '文献調査、Web検索、基礎知識学習',
                'teacher_support': '調査方法指導、信頼性確認',
                'evaluation_method': '調査記録、参考文献リスト'
            },
            {
                'phase': '探究後半',
                'week': '第5-6週',
                'hours': 4,
                'category': '分析・考察',
                'activity': '収集データの分析、仮説検証',
                'teacher_support': '分析手法指導、論理的思考支援',
                'evaluation_method': '分析レポート、考察の深さ'
            },
            {
                'phase': 'まとめ期',
                'week': '第7週',
                'hours': 2,
                'category': '発表準備',
                'activity': 'プレゼンテーション資料作成',
                'teacher_support': '資料作成指導、発表練習',
                'evaluation_method': '資料の完成度、構成'
            },
            {
                'phase': 'まとめ期',
                'week': '第8週',
                'hours': 2,
                'category': '発表会',
                'activity': '最終発表、相互評価',
                'teacher_support': '発表進行、評価基準説明',
                'evaluation_method': '発表内容、質疑応答、相互評価'
            }
        ]
        
        success, message = CurriculumServiceV2.save_curriculum_items(
            sample_curriculum.id, 
            sample_items
        )
        
        if success:
            db.session.commit()
            logger.info(f"Sample curriculum created with ID: {sample_curriculum.id}")
            logger.info(f"Sample items: {len(sample_items)} items added")
            return True
        else:
            db.session.rollback()
            logger.error(f"Failed to create sample curriculum: {message}")
            return False
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sample curriculum: {str(e)}")
        return False

def main():
    """メイン実行関数"""
    logger.info("Starting curriculum v2 migration...")
    
    app = create_app()
    
    with app.app_context():
        # 1. テーブル作成
        if not create_tables():
            logger.error("Failed to create tables. Aborting migration.")
            return False
        
        # 2. 既存データの移行（あれば）
        migrate_sample_data()
        
        # 3. サンプルデータ作成
        create_sample_curriculum()
        
        logger.info("Curriculum v2 migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Access the new curriculum interface at: /curriculum/{id}/view-v2")
        logger.info("2. Edit curriculum using: /curriculum/{id}/edit-v2")
        logger.info("3. Test CSV import/export functionality")
        logger.info("4. Check BaseBuilder integration with category-based problems")
        
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)