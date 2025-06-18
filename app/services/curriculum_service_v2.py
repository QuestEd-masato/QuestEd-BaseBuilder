"""
カリキュラムサービス v2 - シンプル設計
シンプルなテーブル構造でCSVとの整合性を保つ

Author: QuestEd Development Team
Created: 2025-01-15
Version: 2.0.0
"""
import csv
import io
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
from sqlalchemy import text
from app import db
from app.models import Curriculum, User
from app.utils.csv_helper import export_to_csv_utf8_bom

logger = logging.getLogger(__name__)


class CurriculumServiceV2:
    """シンプルなカリキュラムサービス - テーブル構造ベース"""
    
    @classmethod
    def get_curriculum_items(cls, curriculum_id: int) -> List[Dict[str, Any]]:
        """
        カリキュラム項目の取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            カリキュラム項目のリスト
        """
        try:
            # SQLで直接取得（シンプルに）
            query = text("""
                SELECT 
                    ci.*,
                    COUNT(DISTINCT ccp.id) as problem_count
                FROM curriculum_items ci
                LEFT JOIN curriculum_category_problems ccp ON ci.id = ccp.curriculum_item_id
                WHERE ci.curriculum_id = :curriculum_id
                GROUP BY ci.id
                ORDER BY ci.order_index ASC, ci.id ASC
            """)
            
            result = db.session.execute(query, {'curriculum_id': curriculum_id})
            items = []
            
            for row in result:
                items.append({
                    'id': row.id,
                    'phase': row.phase or '',
                    'week': row.week or '',
                    'hours': row.hours or 0,
                    'category': row.category or '',
                    'activity': row.activity or '',
                    'teacher_support': row.teacher_support or '',
                    'evaluation_method': row.evaluation_method or '',
                    'order_index': row.order_index or 0,
                    'problem_count': row.problem_count or 0
                })
            
            logger.info(f"Retrieved {len(items)} curriculum items for curriculum {curriculum_id}")
            return items
            
        except Exception as e:
            logger.error(f"Error getting curriculum items for {curriculum_id}: {str(e)}")
            return []
    
    @classmethod
    def save_curriculum_items(cls, curriculum_id: int, items: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        カリキュラム項目の保存
        
        Args:
            curriculum_id: カリキュラムID
            items: 保存する項目のリスト
            
        Returns:
            (success, message)
        """
        try:
            # トランザクション開始
            # 既存の項目を削除
            db.session.execute(
                text("DELETE FROM curriculum_items WHERE curriculum_id = :id"),
                {'id': curriculum_id}
            )
            
            # 新規項目の追加
            for order_index, item in enumerate(items):
                db.session.execute(text("""
                    INSERT INTO curriculum_items 
                    (curriculum_id, phase, week, hours, category, activity,
                     teacher_support, evaluation_method, order_index)
                    VALUES 
                    (:curriculum_id, :phase, :week, :hours, :category, :activity,
                     :teacher_support, :evaluation_method, :order_index)
                """), {
                    'curriculum_id': curriculum_id,
                    'phase': item.get('phase', ''),
                    'week': item.get('week', ''),
                    'hours': int(item.get('hours', 0)) if str(item.get('hours', 0)).isdigit() else 0,
                    'category': item.get('category', ''),
                    'activity': item.get('activity', ''),
                    'teacher_support': item.get('teacher_support', ''),
                    'evaluation_method': item.get('evaluation_method', ''),
                    'order_index': order_index
                })
            
            # カリキュラムのフォーマットを新形式に更新
            db.session.execute(
                text("UPDATE curriculums SET format = 'table', updated_at = NOW() WHERE id = :id"),
                {'id': curriculum_id}
            )
            
            db.session.commit()
            logger.info(f"Saved {len(items)} curriculum items for curriculum {curriculum_id}")
            return True, f"{len(items)}件のデータを保存しました"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving curriculum items for {curriculum_id}: {str(e)}")
            return False, f"保存エラー: {str(e)}"
    
    @classmethod
    def import_from_csv(cls, curriculum_id: int, csv_content: str) -> Tuple[bool, str]:
        """
        CSVからのインポート
        
        Args:
            curriculum_id: カリキュラムID
            csv_content: CSVファイルの内容
            
        Returns:
            (success, message)
        """
        try:
            # CSVパース
            reader = csv.DictReader(io.StringIO(csv_content))
            items = []
            
            # ヘッダーマッピング（日本語・英語両対応）
            header_mapping = {
                'フェーズ': 'phase', 'phase': 'phase',
                '週': 'week', 'week': 'week',
                '時間数': 'hours', 'hours': 'hours', '時間': 'hours',
                'カテゴリ': 'category', 'category': 'category', 'テーマ': 'category',
                '活動内容': 'activity', 'activity': 'activity',
                '教師のサポート': 'teacher_support', 'teacher_support': 'teacher_support', 'support': 'teacher_support',
                '評価方法': 'evaluation_method', 'evaluation_method': 'evaluation_method', 'evaluation': 'evaluation_method'
            }
            
            for row in reader:
                # ヘッダーを正規化
                normalized_row = {}
                for key, value in row.items():
                    if key and key.strip():
                        normalized_key = header_mapping.get(key.strip(), key.strip().lower())
                        normalized_row[normalized_key] = (value or '').strip()
                
                # 必要なフィールドを抽出
                item = {
                    'phase': normalized_row.get('phase', ''),
                    'week': normalized_row.get('week', ''),
                    'hours': cls._parse_int(normalized_row.get('hours', '0')),
                    'category': normalized_row.get('category', ''),
                    'activity': normalized_row.get('activity', ''),
                    'teacher_support': normalized_row.get('teacher_support', ''),
                    'evaluation_method': normalized_row.get('evaluation_method', '')
                }
                
                # 空行でなければ追加
                if any(item.values()):
                    items.append(item)
            
            if not items:
                return False, "有効なデータが見つかりませんでした"
            
            # データを保存
            success, message = cls.save_curriculum_items(curriculum_id, items)
            if success:
                return True, f"{len(items)}件のデータをインポートしました"
            else:
                return False, message
                
        except Exception as e:
            logger.error(f"CSV import error for curriculum {curriculum_id}: {str(e)}")
            return False, f"インポートエラー: {str(e)}"
    
    @classmethod
    def export_to_csv(cls, curriculum_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        CSV形式でのエクスポート
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            (csv_data, error_message)
        """
        try:
            items = cls.get_curriculum_items(curriculum_id)
            
            if not items:
                return None, "エクスポートするデータがありません"
            
            # CSV用のデータ形式に変換
            csv_data = []
            for item in items:
                csv_data.append({
                    'フェーズ': item.get('phase', ''),
                    '週': item.get('week', ''),
                    '時間数': item.get('hours', 0),
                    'カテゴリ': item.get('category', ''),
                    '活動内容': item.get('activity', ''),
                    '教師のサポート': item.get('teacher_support', ''),
                    '評価方法': item.get('evaluation_method', '')
                })
            
            logger.info(f"Generated CSV data for curriculum {curriculum_id}: {len(csv_data)} rows")
            return csv_data, None
            
        except Exception as e:
            logger.error(f"Error exporting curriculum {curriculum_id}: {str(e)}")
            return None, f"エクスポートエラー: {str(e)}"
    
    @classmethod
    def get_related_problems(cls, category: str, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        カテゴリに関連する問題を取得
        
        Args:
            category: カテゴリ名
            student_id: 学生ID（正答率計算用）
            
        Returns:
            関連問題のリスト
        """
        try:
            # まず完全一致を試行
            exact_match_query = text("""
                SELECT 
                    pc.id as category_id,
                    pc.name as category_name,
                    COUNT(DISTINCT bki.id) as total_problems,
                    COALESCE(AVG(CASE WHEN ar.is_correct THEN 100 ELSE 0 END), 0) as avg_score
                FROM problem_categories pc
                INNER JOIN basic_knowledge_items bki ON pc.id = bki.category_id
                LEFT JOIN answer_records ar ON bki.id = ar.item_id 
                    AND (:student_id IS NULL OR ar.student_id = :student_id)
                WHERE pc.name = :category
                GROUP BY pc.id, pc.name
                HAVING total_problems > 0
            """)
            
            result = db.session.execute(exact_match_query, {
                'category': category,
                'student_id': student_id
            })
            
            problems = []
            for row in result:
                problems.append({
                    'category_id': row.category_id,
                    'category_name': row.category_name,
                    'total_problems': row.total_problems,
                    'avg_score': float(row.avg_score or 0),
                    'match_type': 'exact'
                })
            
            # 完全一致がない場合は部分一致を試行
            if not problems:
                partial_match_query = text("""
                    SELECT 
                        pc.id as category_id,
                        pc.name as category_name,
                        COUNT(DISTINCT bki.id) as total_problems,
                        COALESCE(AVG(CASE WHEN ar.is_correct THEN 100 ELSE 0 END), 0) as avg_score,
                        CASE 
                            WHEN pc.name LIKE :category_start THEN 1
                            WHEN pc.name LIKE :category_mid THEN 2
                            WHEN pc.description LIKE :category_desc THEN 3
                            ELSE 4
                        END as match_priority
                    FROM problem_categories pc
                    INNER JOIN basic_knowledge_items bki ON pc.id = bki.category_id
                    LEFT JOIN answer_records ar ON bki.id = ar.item_id 
                        AND (:student_id IS NULL OR ar.student_id = :student_id)
                    WHERE pc.name LIKE :category_pattern 
                       OR pc.description LIKE :category_pattern
                       OR pc.name LIKE :category_words
                    GROUP BY pc.id, pc.name
                    HAVING total_problems > 0
                    ORDER BY match_priority ASC, total_problems DESC
                    LIMIT 5
                """)
                
                # カテゴリ名を単語に分割して検索パターンを生成
                category_words = ' '.join([f'%{word}%' for word in category.split() if len(word) > 1])
                
                result = db.session.execute(partial_match_query, {
                    'category_start': f'{category}%',
                    'category_mid': f'%{category}%',
                    'category_desc': f'%{category}%',
                    'category_pattern': f'%{category}%',
                    'category_words': category_words,
                    'student_id': student_id
                })
                
                for row in result:
                    problems.append({
                        'category_id': row.category_id,
                        'category_name': row.category_name,
                        'total_problems': row.total_problems,
                        'avg_score': float(row.avg_score or 0),
                        'match_type': 'partial'
                    })
            
            logger.debug(f"Found {len(problems)} related problem categories for '{category}'")
            return problems
            
        except Exception as e:
            logger.error(f"Error getting related problems for '{category}': {str(e)}")
            return []
    
    @classmethod
    def generate_review_problems(cls, curriculum_item_id: int, student_id: int) -> List[Dict[str, Any]]:
        """
        復習問題の生成
        
        Args:
            curriculum_item_id: カリキュラム項目ID
            student_id: 学生ID
            
        Returns:
            復習問題のリスト
        """
        try:
            # カリキュラム項目の情報を取得
            item_result = db.session.execute(text("""
                SELECT category FROM curriculum_items WHERE id = :id
            """), {'id': curriculum_item_id})
            
            item = item_result.first()
            if not item or not item.category:
                return []
            
            # カテゴリに基づいて低正答率の問題を取得
            query = text("""
                SELECT 
                    bki.id,
                    bki.title,
                    bki.question,
                    bki.choices,
                    COALESCE(ar.correct_rate, 0) as correct_rate
                FROM basic_knowledge_items bki
                INNER JOIN problem_categories pc ON bki.category_id = pc.id
                LEFT JOIN (
                    SELECT 
                        item_id,
                        AVG(CASE WHEN is_correct THEN 100 ELSE 0 END) as correct_rate
                    FROM answer_records
                    WHERE student_id = :student_id
                    GROUP BY item_id
                ) ar ON bki.id = ar.item_id
                WHERE pc.name LIKE :category OR pc.description LIKE :category
                ORDER BY COALESCE(ar.correct_rate, 0) ASC, RAND()
                LIMIT 10
            """)
            
            result = db.session.execute(query, {
                'category': f'%{item.category}%',
                'student_id': student_id
            })
            
            problems = []
            for row in result:
                problems.append({
                    'id': row.id,
                    'title': row.title or '',
                    'question': row.question or '',
                    'choices': row.choices or '',
                    'correct_rate': float(row.correct_rate or 0)
                })
            
            logger.debug(f"Generated {len(problems)} review problems for item {curriculum_item_id}")
            return problems
            
        except Exception as e:
            logger.error(f"Error generating review problems for item {curriculum_item_id}: {str(e)}")
            return []
    
    @classmethod
    def get_curriculum_stats(cls, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムの統計情報を取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            統計情報
        """
        try:
            items = cls.get_curriculum_items(curriculum_id)
            
            if not items:
                return {
                    'total_items': 0,
                    'total_hours': 0,
                    'phases': [],
                    'categories': []
                }
            
            # 統計計算
            total_hours = sum(item.get('hours', 0) for item in items)
            phases = list(set(item.get('phase', '') for item in items if item.get('phase')))
            categories = list(set(item.get('category', '') for item in items if item.get('category')))
            
            return {
                'total_items': len(items),
                'total_hours': total_hours,
                'phases': sorted(phases),
                'categories': sorted(categories),
                'avg_hours_per_item': round(total_hours / len(items), 1) if items else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting curriculum stats for {curriculum_id}: {str(e)}")
            return {
                'total_items': 0,
                'total_hours': 0,
                'phases': [],
                'categories': []
            }
    
    @classmethod
    def migrate_from_json(cls, curriculum_id: int) -> Tuple[bool, str]:
        """
        JSONフォーマットから新フォーマットへの移行
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            (success, message)
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return False, "カリキュラムが見つかりません"
            
            if curriculum.format == 'table':
                return True, "既に新形式です"
            
            # JSONコンテンツをパース
            if not curriculum.content:
                return False, "移行するデータがありません"
            
            try:
                content = json.loads(curriculum.content)
            except json.JSONDecodeError:
                return False, "JSONデータが無効です"
            
            # JSONから項目を抽出
            items = []
            phases = content.get('phases', [])
            
            for phase in phases:
                phase_name = phase.get('name', phase.get('phase', ''))
                weeks = phase.get('weeks', [])
                
                for week in weeks:
                    items.append({
                        'phase': phase_name,
                        'week': week.get('week', ''),
                        'hours': cls._parse_int(week.get('hours', 0)),
                        'category': week.get('theme', week.get('category', '')),
                        'activity': week.get('activities', ''),
                        'teacher_support': week.get('teacher_support', ''),
                        'evaluation_method': week.get('evaluation', '')
                    })
            
            if not items:
                # フェーズ構造がない場合の基本変換
                items = [{
                    'phase': '学習フェーズ',
                    'week': '第1週',
                    'hours': curriculum.total_hours or 35,
                    'category': curriculum.title,
                    'activity': content.get('overview', ''),
                    'teacher_support': '',
                    'evaluation_method': ''
                }]
            
            # 新形式で保存
            success, message = cls.save_curriculum_items(curriculum_id, items)
            if success:
                return True, f"移行完了: {len(items)}件のデータを変換しました"
            else:
                return False, f"移行失敗: {message}"
                
        except Exception as e:
            logger.error(f"Migration error for curriculum {curriculum_id}: {str(e)}")
            return False, f"移行エラー: {str(e)}"
    
    @staticmethod
    def _parse_int(value: Any) -> int:
        """安全な整数変換"""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0