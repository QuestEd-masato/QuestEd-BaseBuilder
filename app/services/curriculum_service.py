"""
カリキュラムデータの処理を統一的に扱うサービスクラス
データ構造の一貫性を保証し、エラーハンドリングを一元化

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models import Curriculum, Class
from app import db


class CurriculumService:
    """カリキュラム関連の処理を担当するサービスクラス"""
    
    # デフォルトのカリキュラム構造定義
    DEFAULT_STRUCTURE = {
        'phases': [],
        'rubric_suggestion': [],
        'overview': '',
        'objectives': [],
        'schedule': [],
        'assessment': {
            'methods': [],
            'criteria': []
        },
        'resources': [],
        'total_hours': 0,
        'has_fieldwork': False,
        'fieldwork_count': 0,
        'has_presentation': False,
        'presentation_format': '',
        'group_work_level': 'medium',
        'external_collaboration': False
    }
    
    @staticmethod
    def parse_curriculum_content(curriculum: Curriculum) -> Dict[str, Any]:
        """
        カリキュラムのcontentをパースして統一された形式で返す
        
        Args:
            curriculum: Curriculumモデルインスタンス
            
        Returns:
            統一された形式のカリキュラムデータ
        """
        logger = logging.getLogger(__name__)
        
        # デフォルトの構造をコピー
        default_structure = CurriculumService.DEFAULT_STRUCTURE.copy()
        
        # contentが空の場合
        if not curriculum.content:
            logger.info(f"Curriculum ID {curriculum.id} has empty content, using default structure")
            return default_structure
        
        try:
            # JSONパース
            content = json.loads(curriculum.content)
            
            # コンテンツが文字列の場合（レガシーデータ対応）
            if isinstance(content, str):
                logger.warning(f"Curriculum ID {curriculum.id} has string content, converting to structure")
                return {
                    **default_structure,
                    'overview': content,
                    'phases': [{
                        'name': '学習フェーズ',
                        'description': content,
                        'weeks': []
                    }]
                }
            
            # デフォルト構造とマージ（再帰的）
            result = CurriculumService._merge_dict_recursive(default_structure, content)
            
            # データ型検証と修正
            result = CurriculumService._validate_and_fix_structure(result)
            
            logger.debug(f"Successfully parsed curriculum content for ID {curriculum.id}")
            return result
            
        except json.JSONDecodeError as e:
            # JSONパースエラーの場合
            logger.error(f"Failed to parse curriculum content for ID {curriculum.id}: {str(e)}")
            return default_structure
        except Exception as e:
            # その他のエラー
            logger.error(f"Error processing curriculum content for ID {curriculum.id}: {str(e)}")
            return default_structure
    
    @staticmethod
    def _merge_dict_recursive(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """辞書を再帰的にマージ"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = CurriculumService._merge_dict_recursive(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def _validate_and_fix_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """データ構造の検証と修正"""
        
        # phasesの検証（辞書から配列への変換対応）
        if isinstance(data.get('phases'), dict):
            data['phases'] = list(data['phases'].values())
        elif not isinstance(data.get('phases'), list):
            data['phases'] = []
        
        # rubric_suggestionの検証
        if not isinstance(data.get('rubric_suggestion'), list):
            data['rubric_suggestion'] = []
        
        # objectivesの検証
        if not isinstance(data.get('objectives'), list):
            data['objectives'] = []
        
        # scheduleの検証
        if not isinstance(data.get('schedule'), list):
            data['schedule'] = []
        
        # resourcesの検証
        if not isinstance(data.get('resources'), list):
            data['resources'] = []
        
        # assessmentの検証
        if not isinstance(data.get('assessment'), dict):
            data['assessment'] = {'methods': [], 'criteria': []}
        else:
            if not isinstance(data['assessment'].get('methods'), list):
                data['assessment']['methods'] = []
            if not isinstance(data['assessment'].get('criteria'), list):
                data['assessment']['criteria'] = []
        
        # 数値フィールドの検証
        numeric_fields = ['total_hours', 'fieldwork_count']
        for field in numeric_fields:
            try:
                data[field] = int(data.get(field, 0))
            except (ValueError, TypeError):
                data[field] = 0
        
        # ブール値フィールドの検証
        boolean_fields = ['has_fieldwork', 'has_presentation', 'external_collaboration']
        for field in boolean_fields:
            data[field] = bool(data.get(field, False))
        
        # 文字列フィールドの検証
        string_fields = ['overview', 'presentation_format', 'group_work_level']
        for field in string_fields:
            if not isinstance(data.get(field), str):
                data[field] = data.get(field, '')
        
        return data
    
    @staticmethod
    def get_curriculum_display_data(curriculum: Curriculum) -> Dict[str, Any]:
        """
        テンプレート表示用のカリキュラムデータを取得
        
        Args:
            curriculum: Curriculumモデルインスタンス
            
        Returns:
            テンプレート用の完全なデータセット
        """
        # パース済みのコンテンツを取得
        curriculum_data = CurriculumService.parse_curriculum_content(curriculum)
        
        # 表示用データの構築
        display_data = {
            'id': curriculum.id,
            'title': curriculum.title,
            'description': curriculum.description,
            'created_at': curriculum.created_at,
            'updated_at': curriculum.updated_at,
            'teacher_id': curriculum.teacher_id,
            'class_id': curriculum.class_id,
            # パース済みデータを展開
            **curriculum_data
        }
        
        # カリキュラムの統計情報を計算
        display_data.update(CurriculumService._calculate_curriculum_stats(curriculum_data))
        
        return display_data
    
    @staticmethod
    def _calculate_curriculum_stats(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
        """カリキュラムの統計情報を計算"""
        stats = {
            'calculated_total_hours': 0,
            'total_phases': len(curriculum_data.get('phases', [])),
            'total_objectives': len(curriculum_data.get('objectives', [])),
            'total_resources': len(curriculum_data.get('resources', [])),
            'has_assessment': bool(curriculum_data.get('assessment', {}).get('methods')),
            'completion_percentage': 0
        }
        
        # フェーズごとの総時間を計算
        total_hours = 0
        total_activities = 0
        
        for phase in curriculum_data.get('phases', []):
            for week in phase.get('weeks', []):
                total_hours += week.get('hours', 0)
                total_activities += len(week.get('activities', []))
        
        stats['calculated_total_hours'] = total_hours
        stats['total_activities'] = total_activities
        
        # 完成度の計算（概算）
        completion_score = 0
        max_score = 6
        
        if curriculum_data.get('overview'):
            completion_score += 1
        if curriculum_data.get('objectives'):
            completion_score += 1
        if curriculum_data.get('phases'):
            completion_score += 1
        if curriculum_data.get('assessment', {}).get('methods'):
            completion_score += 1
        if curriculum_data.get('resources'):
            completion_score += 1
        if total_hours > 0:
            completion_score += 1
        
        stats['completion_percentage'] = round((completion_score / max_score) * 100)
        
        return stats
    
    @staticmethod
    def update_curriculum_content(curriculum: Curriculum, content_data: Dict[str, Any]) -> bool:
        """
        カリキュラムのcontentを更新
        
        Args:
            curriculum: Curriculumモデルインスタンス
            content_data: 更新するコンテンツデータ
            
        Returns:
            更新成功の可否
        """
        logger = logging.getLogger(__name__)
        
        try:
            # 既存のコンテンツを取得
            current_data = CurriculumService.parse_curriculum_content(curriculum)
            
            # 新しいデータとマージ
            updated_data = CurriculumService._merge_dict_recursive(current_data, content_data)
            
            # データ構造の検証
            validated_data = CurriculumService._validate_and_fix_structure(updated_data)
            
            # JSON文字列に変換して保存
            curriculum.content = json.dumps(validated_data, ensure_ascii=False, indent=2)
            curriculum.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Successfully updated curriculum content for ID {curriculum.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update curriculum content for ID {curriculum.id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_curriculum_from_ai_data(ai_data: Dict[str, Any], class_id: int, teacher_id: int, title: str, description: str = '') -> Optional[Curriculum]:
        """
        AI生成データからカリキュラムを作成
        
        Args:
            ai_data: AI生成されたカリキュラムデータ
            class_id: クラスID
            teacher_id: 教師ID
            title: カリキュラムタイトル
            description: カリキュラム説明
            
        Returns:
            作成されたCurriculumインスタンス、失敗時はNone
        """
        logger = logging.getLogger(__name__)
        
        try:
            # AI データを標準構造に変換
            normalized_data = CurriculumService._normalize_ai_data(ai_data)
            
            # カリキュラムインスタンスを作成
            curriculum = Curriculum(
                class_id=class_id,
                teacher_id=teacher_id,
                title=title,
                description=description,
                content=json.dumps(normalized_data, ensure_ascii=False, indent=2)
            )
            
            db.session.add(curriculum)
            db.session.commit()
            
            logger.info(f"Successfully created curriculum from AI data: ID {curriculum.id}")
            return curriculum
            
        except Exception as e:
            logger.error(f"Failed to create curriculum from AI data: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def _normalize_ai_data(ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI生成データを標準構造に正規化"""
        normalized = CurriculumService.DEFAULT_STRUCTURE.copy()
        
        # AI データのマッピング
        if 'overview' in ai_data:
            normalized['overview'] = ai_data['overview']
        
        if 'objectives' in ai_data:
            normalized['objectives'] = ai_data['objectives'] if isinstance(ai_data['objectives'], list) else []
        
        if 'schedule' in ai_data:
            normalized['schedule'] = ai_data['schedule'] if isinstance(ai_data['schedule'], list) else []
            # scheduleからphasesを生成
            normalized['phases'] = CurriculumService._convert_schedule_to_phases(ai_data['schedule'])
        
        if 'assessment' in ai_data:
            normalized['assessment'] = ai_data['assessment'] if isinstance(ai_data['assessment'], dict) else {}
        
        if 'resources' in ai_data:
            normalized['resources'] = ai_data['resources'] if isinstance(ai_data['resources'], list) else []
        
        return normalized
    
    @staticmethod
    def _convert_schedule_to_phases(schedule: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """スケジュールデータをフェーズ形式に変換"""
        phases = []
        
        for item in schedule:
            if isinstance(item, dict):
                phase = {
                    'name': item.get('phase', '学習フェーズ'),
                    'description': item.get('description', ''),
                    'duration': item.get('duration', ''),
                    'activities': item.get('activities', []),
                    'milestones': item.get('milestones', []),
                    'weeks': []
                }
                phases.append(phase)
        
        return phases
    
    @staticmethod
    def validate_curriculum_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        カリキュラムデータの妥当性を検証
        
        Args:
            data: 検証するデータ
            
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # 必須フィールドの確認
        if not data.get('overview'):
            errors.append('カリキュラムの概要は必須です')
        
        if not data.get('objectives'):
            errors.append('学習目標を少なくとも1つ設定してください')
        
        # データ型の確認
        if not isinstance(data.get('phases', []), list):
            errors.append('フェーズデータの形式が正しくありません')
        
        if not isinstance(data.get('assessment', {}), dict):
            errors.append('評価データの形式が正しくありません')
        
        # 数値の範囲確認
        total_hours = data.get('total_hours', 0)
        if not isinstance(total_hours, (int, float)) or total_hours < 0:
            errors.append('総時間数は0以上の数値で入力してください')
        
        return len(errors) == 0, errors