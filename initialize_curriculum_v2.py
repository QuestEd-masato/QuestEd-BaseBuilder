#!/usr/bin/env python3
"""
カリキュラム機能v2 初期化スクリプト
- curriculum_itemsテーブルの作成
- カリキュラムID=7の初期データ作成
- BaseBuilder連携テーブルの確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from config import Config
from sqlalchemy import text
from datetime import datetime

def create_app():
    """フラスクアプリケーションの作成"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 拡張機能の初期化
    db.init_app(app)
    
    return app

def check_and_create_tables():
    """必要なテーブルの確認と作成"""
    print("=== テーブル構造の確認・作成 ===")
    
    # curriculum_itemsテーブルの存在確認
    result = db.session.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'curriculum_items'
    """)).first()
    
    if result.count == 0:
        print("curriculum_itemsテーブルが存在しません。作成します...")
        
        # テーブル作成
        db.session.execute(text("""
            CREATE TABLE curriculum_items (
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
        print("✓ curriculum_itemsテーブルを作成しました")
    else:
        print("✓ curriculum_itemsテーブルは既に存在します")
    
    # curriculum_category_problemsテーブルの存在確認
    result = db.session.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'curriculum_category_problems'
    """)).first()
    
    if result.count == 0:
        print("curriculum_category_problemsテーブルが存在しません。作成します...")
        
        db.session.execute(text("""
            CREATE TABLE curriculum_category_problems (
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
        print("✓ curriculum_category_problemsテーブルを作成しました")
    else:
        print("✓ curriculum_category_problemsテーブルは既に存在します")
    
    # curriculumsテーブルのformat列追加
    try:
        db.session.execute(text("""
            ALTER TABLE curriculums 
            ADD COLUMN IF NOT EXISTS format VARCHAR(20) DEFAULT 'json'
            COMMENT 'データ形式: json(レガシー) | table(新形式)'
        """))
        print("✓ curriculumsテーブルにformat列を追加しました")
    except Exception as e:
        print(f"format列の追加をスキップしました: {str(e)}")
    
    db.session.commit()

def check_curriculum_7():
    """カリキュラムID=7の存在確認"""
    print("\n=== カリキュラムID=7の確認 ===")
    
    result = db.session.execute(text("""
        SELECT id, title, class_id, teacher_id, format 
        FROM curriculums 
        WHERE id = 7
    """)).first()
    
    if result:
        print(f"✓ カリキュラムID=7が見つかりました:")
        print(f"  - タイトル: {result.title}")
        print(f"  - クラスID: {result.class_id}")
        print(f"  - 教師ID: {result.teacher_id}")
        print(f"  - フォーマット: {result.format or 'json'}")
        return True
    else:
        print("✗ カリキュラムID=7が見つかりません")
        return False

def create_sample_data():
    """カリキュラムID=7の初期データ作成"""
    print("\n=== 初期データの作成 ===")
    
    # 既存データの確認
    existing_count = db.session.execute(text("""
        SELECT COUNT(*) as count FROM curriculum_items WHERE curriculum_id = 7
    """)).first().count
    
    if existing_count > 0:
        print(f"✓ カリキュラムID=7には既に{existing_count}件の項目があります")
        return
    
    # 初期データの作成
    sample_items = [
        {
            'phase': '準備期',
            'week': '第1週',
            'hours': 2,
            'category': '基礎知識',
            'activity': '探究活動の基礎概念の理解',
            'teacher_support': '概念説明と事例紹介',
            'evaluation_method': '理解度確認テスト',
            'order_index': 1
        },
        {
            'phase': '準備期',
            'week': '第2週',
            'hours': 2,
            'category': '情報収集',
            'activity': '情報収集手法の学習',
            'teacher_support': '検索技術の指導',
            'evaluation_method': '情報収集レポート',
            'order_index': 2
        },
        {
            'phase': '探究前半',
            'week': '第3-4週',
            'hours': 4,
            'category': '問題発見',
            'activity': 'テーマ設定と問題の明確化',
            'teacher_support': '個別指導とテーマ調整',
            'evaluation_method': '問題設定シート',
            'order_index': 3
        },
        {
            'phase': '探究前半',
            'week': '第5-8週',
            'hours': 8,
            'category': '調査・実験',
            'activity': '仮説設定と調査・実験の実施',
            'teacher_support': '実験方法の指導と安全確保',
            'evaluation_method': '実験ノートの評価',
            'order_index': 4
        },
        {
            'phase': '探究後半',
            'week': '第9-12週',
            'hours': 8,
            'category': 'データ分析',
            'activity': 'データ分析と考察',
            'teacher_support': '分析手法の指導',
            'evaluation_method': '分析レポート',
            'order_index': 5
        },
        {
            'phase': '探究後半',
            'week': '第13-14週',
            'hours': 4,
            'category': 'まとめ',
            'activity': '結論の整理と発表準備',
            'teacher_support': 'プレゼンテーション指導',
            'evaluation_method': '発表練習の評価',
            'order_index': 6
        },
        {
            'phase': '発表期',
            'week': '第15週',
            'hours': 2,
            'category': 'プレゼンテーション',
            'activity': '研究成果の発表',
            'teacher_support': '発表進行と質疑応答支援',
            'evaluation_method': '発表評価とピア評価',
            'order_index': 7
        }
    ]
    
    for item in sample_items:
        db.session.execute(text("""
            INSERT INTO curriculum_items 
            (curriculum_id, phase, week, hours, category, activity, teacher_support, evaluation_method, order_index)
            VALUES (:curriculum_id, :phase, :week, :hours, :category, :activity, :teacher_support, :evaluation_method, :order_index)
        """), {
            'curriculum_id': 7,
            **item
        })
    
    # カリキュラムのフォーマットを更新
    db.session.execute(text("""
        UPDATE curriculums 
        SET format = 'table', updated_at = :now 
        WHERE id = 7
    """), {'now': datetime.now()})
    
    db.session.commit()
    print(f"✓ カリキュラムID=7に{len(sample_items)}件の初期データを作成しました")

def check_basebuilder_data():
    """BaseBuilderデータの確認"""
    print("\n=== BaseBuilderデータの確認 ===")
    
    # problem_categoriesテーブルの確認
    try:
        category_count = db.session.execute(text("""
            SELECT COUNT(*) as count FROM problem_categories
        """)).first().count
        print(f"✓ problem_categoriesテーブル: {category_count}件")
        
        # 上位5件を表示
        if category_count > 0:
            categories = db.session.execute(text("""
                SELECT name FROM problem_categories LIMIT 5
            """)).fetchall()
            print("  サンプル:")
            for cat in categories:
                print(f"    - {cat.name}")
    except Exception as e:
        print(f"✗ problem_categoriesテーブルの確認エラー: {str(e)}")
    
    # text_setsテーブルの確認
    try:
        text_count = db.session.execute(text("""
            SELECT COUNT(*) as count FROM text_sets
        """)).first().count
        print(f"✓ text_setsテーブル: {text_count}件")
        
        # 上位5件を表示
        if text_count > 0:
            texts = db.session.execute(text("""
                SELECT title FROM text_sets LIMIT 5
            """)).fetchall()
            print("  サンプル:")
            for text in texts:
                print(f"    - {text.title}")
    except Exception as e:
        print(f"✗ text_setsテーブルの確認エラー: {str(e)}")

def main():
    """メイン処理"""
    print("QuestEd カリキュラム機能v2 初期化スクリプト")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # テーブル作成
            check_and_create_tables()
            
            # カリキュラムID=7の確認
            curriculum_exists = check_curriculum_7()
            
            if curriculum_exists:
                # 初期データ作成
                create_sample_data()
                
                # BaseBuilderデータ確認
                check_basebuilder_data()
                
                print("\n" + "=" * 50)
                print("✓ 初期化が完了しました！")
                print("カリキュラムID=7にアクセスして統合機能を確認してください。")
                print("URL: /teacher/curriculum/7")
            else:
                print("\n" + "=" * 50)
                print("✗ カリキュラムID=7が見つかりません")
                print("事前にカリキュラムを作成してから再実行してください。")
                
        except Exception as e:
            print(f"\n✗ 初期化中にエラーが発生しました: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())