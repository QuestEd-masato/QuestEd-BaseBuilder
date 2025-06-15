"""
データベースクリーンアップ用マイグレーション

このスクリプトは以下の最適化を実行します：
1. 未使用カラムの削除
2. データ型の最適化
3. 必要なインデックスの追加

注意: 本番環境では十分なテストとバックアップを取ってから実行してください。
"""

from flask import current_app
from extensions import db
import logging

logger = logging.getLogger(__name__)

def cleanup_unused_columns():
    """未使用カラムの削除"""
    try:
        # 本番環境では手動で実行することを推奨
        if current_app.config.get('ENV') == 'production':
            logger.warning("本番環境での自動カラム削除はスキップされます。手動で実行してください。")
            return
        
        cleanup_queries = [
            # Userテーブルの未使用カラム削除
            "ALTER TABLE users DROP COLUMN IF EXISTS email_token",
            "ALTER TABLE users DROP COLUMN IF EXISTS token_created_at", 
            "ALTER TABLE users DROP COLUMN IF EXISTS reset_token",
            "ALTER TABLE users DROP COLUMN IF EXISTS reset_token_created_at",
            
            # ActivityLogテーブルの重複カラム削除
            "ALTER TABLE activity_logs DROP COLUMN IF EXISTS activity",
            
            # ProficiencyRecordテーブルの重複カラム削除
            "ALTER TABLE proficiency_records DROP COLUMN IF EXISTS last_updated",
            
            # BasicKnowledgeItemテーブルの未使用カラム削除
            "ALTER TABLE basic_knowledge_items DROP COLUMN IF EXISTS answer_type"
        ]
        
        for query in cleanup_queries:
            try:
                db.session.execute(query)
                logger.info(f"実行成功: {query}")
            except Exception as e:
                logger.warning(f"カラム削除スキップ (既に存在しない可能性): {query} - {str(e)}")
        
        db.session.commit()
        logger.info("未使用カラムの削除が完了しました")
        
    except Exception as e:
        logger.error(f"未使用カラム削除エラー: {str(e)}")
        db.session.rollback()
        raise

def optimize_data_types():
    """データ型の最適化"""
    try:
        # MySQL/PostgreSQL用のJSON型変更クエリ
        optimization_queries = [
            # JSONデータを適切な型に変更
            "ALTER TABLE interest_surveys MODIFY COLUMN responses JSON",
            "ALTER TABLE personality_surveys MODIFY COLUMN responses JSON", 
            "ALTER TABLE basic_knowledge_items MODIFY COLUMN choices JSON",
            "ALTER TABLE learning_paths MODIFY COLUMN steps JSON",
            "ALTER TABLE curriculums MODIFY COLUMN content JSON",
            "ALTER TABLE rubric_templates MODIFY COLUMN content JSON"
        ]
        
        for query in optimization_queries:
            try:
                db.session.execute(query)
                logger.info(f"型変更成功: {query}")
            except Exception as e:
                logger.warning(f"型変更スキップ (既に適切な型、またはSQLite): {query} - {str(e)}")
        
        db.session.commit()
        logger.info("データ型の最適化が完了しました")
        
    except Exception as e:
        logger.error(f"データ型最適化エラー: {str(e)}")
        db.session.rollback()
        raise

def add_performance_indexes():
    """パフォーマンス向上のためのインデックス追加"""
    try:
        index_queries = [
            # 頻繁に検索されるカラムのインデックス
            "CREATE INDEX IF NOT EXISTS idx_proficiency_student_category ON proficiency_records(student_id, category_id)",
            "CREATE INDEX IF NOT EXISTS idx_proficiency_last_reviewed ON proficiency_records(last_reviewed)",
            "CREATE INDEX IF NOT EXISTS idx_word_proficiency_student_problem ON word_proficiency_records(student_id, problem_id)",
            "CREATE INDEX IF NOT EXISTS idx_word_proficiency_review_date ON word_proficiency_records(review_date)",
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_student_date ON activity_logs(student_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_ai_recommendations_type ON ai_recommendations(recommendation_type)",
            "CREATE INDEX IF NOT EXISTS idx_ai_recommendations_session ON ai_recommendations(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_student_weaknesses_category ON student_weaknesses(student_id, category, subcategory)",
            "CREATE INDEX IF NOT EXISTS idx_student_weaknesses_active ON student_weaknesses(is_active)",
            
            # ユーザー関連の頻繁な検索
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_users_school ON users(school_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_verified ON users(is_verified)",
            
            # 学習関連の頻繁な検索
            "CREATE INDEX IF NOT EXISTS idx_student_unit_selections_student ON student_unit_selections(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_student_unit_selections_status ON student_unit_selections(status)",
            "CREATE INDEX IF NOT EXISTS idx_student_unit_selections_last_activity ON student_unit_selections(last_activity_at)"
        ]
        
        for query in index_queries:
            try:
                db.session.execute(query)
                logger.info(f"インデックス作成成功: {query}")
            except Exception as e:
                logger.warning(f"インデックス作成スキップ (既に存在): {query} - {str(e)}")
        
        db.session.commit()
        logger.info("パフォーマンスインデックスの追加が完了しました")
        
    except Exception as e:
        logger.error(f"インデックス追加エラー: {str(e)}")
        db.session.rollback()
        raise

def run_database_cleanup():
    """データベースクリーンアップの実行"""
    try:
        logger.info("データベースクリーンアップを開始します...")
        
        # ステップ1: 未使用カラムの削除
        cleanup_unused_columns()
        
        # ステップ2: データ型の最適化 
        optimize_data_types()
        
        # ステップ3: パフォーマンスインデックスの追加
        add_performance_indexes()
        
        logger.info("データベースクリーンアップが正常に完了しました")
        return True
        
    except Exception as e:
        logger.error(f"データベースクリーンアップエラー: {str(e)}")
        return False

if __name__ == "__main__":
    # スタンドアロン実行時
    from app import create_app
    
    app = create_app()
    with app.app_context():
        success = run_database_cleanup()
        if success:
            print("データベースクリーンアップが完了しました")
        else:
            print("データベースクリーンアップ中にエラーが発生しました")