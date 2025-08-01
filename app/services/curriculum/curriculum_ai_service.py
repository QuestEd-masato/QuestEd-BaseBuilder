# -*- coding: utf-8 -*-
"""
CurriculumAIService

AI統合によるカリキュラム生成を管理する専門サービス
Phase8C: curriculum_management.pyのgenerate_curriculum()から分離
"""
import json
import logging
from typing import Dict, Any

from flask import current_app

from app.ai import generate_curriculum_with_ai
from app.models import Class, MainTheme

logger = logging.getLogger(__name__)


class CurriculumAIService:
    """AI統合カリキュラム生成専門サービス"""

    def generate_curriculum_with_ai_integration(self, class_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AIを使用してカリキュラムを生成
        
        Args:
            class_id: クラスID
            form_data: フォームデータ
            
        Returns:
            Dict: 生成結果
        """
        try:
            # クラス情報取得
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "success": False,
                    "message": "クラスが見つかりません"
                }

            # フォームデータの正規化
            normalized_data = self._normalize_form_data(form_data)
            
            # AI生成タイプの判定
            if normalized_data.get("include_detailed_tasks"):
                # 詳細タスク付きカリキュラム生成
                return self._generate_detailed_curriculum_with_tasks(class_obj, normalized_data)
            else:
                # 標準カリキュラム生成
                return self._generate_standard_curriculum(class_obj, normalized_data)

        except Exception as e:
            logger.error(f"Error in AI curriculum generation: {str(e)}")
            return self._create_fallback_curriculum(class_obj, form_data)

    def _normalize_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        フォームデータを正規化
        
        Args:
            form_data: 生のフォームデータ
            
        Returns:
            Dict: 正規化されたデータ
        """
        return {
            "title": form_data.get("title", ""),
            "description": form_data.get("description", ""),
            "main_theme_id": form_data.get("main_theme_id"),
            "total_classes": int(form_data.get("total_classes", 35)),
            "total_hours": float(form_data.get("total_hours", 29.2)),
            "difficulty_level": int(form_data.get("difficulty_level", 2)),
            "mastery_threshold": int(form_data.get("mastery_threshold", 80)),
            "self_paced_mode": form_data.get("self_paced_mode", "flexible"),
            "prerequisite_skills": form_data.get("prerequisite_skills", ""),
            "has_fieldwork": form_data.get("has_fieldwork", False),
            "fieldwork_count": int(form_data.get("fieldwork_count", 0)),
            "has_presentation": form_data.get("has_presentation", False),
            "presentation_format": form_data.get("presentation_format", "プレゼンテーション"),
            "group_work_level": form_data.get("group_work_level", "ハイブリッド"),
            "external_collaboration": form_data.get("external_collaboration", False),
            "include_detailed_tasks": form_data.get("include_detailed_tasks", False),
            "default_task_types": form_data.get("default_task_types", []),
            "submission_formats": form_data.get("submission_formats", []),
            "tasks_per_week": int(form_data.get("tasks_per_week", 3)),
            "task_difficulty_distribution": form_data.get("task_difficulty_distribution", "mixed"),
            "auto_generate_rubrics": form_data.get("auto_generate_rubrics", False),
            "enable_auto_approval": form_data.get("enable_auto_approval", False),
            "ai_generate_tasks": form_data.get("ai_generate_tasks", False),
            "task_generation_prompt": form_data.get("task_generation_prompt", "")
        }

    def _generate_detailed_curriculum_with_tasks(self, class_obj: Class, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        詳細タスク付きカリキュラムを生成
        
        Args:
            class_obj: クラスオブジェクト
            data: 正規化されたデータ
            
        Returns:
            Dict: 生成結果
        """
        try:
            # クラス詳細情報の準備
            class_details = {
                'name': class_obj.name,
                'description': class_obj.description or f"{class_obj.name}クラス",
                'teacher_name': class_obj.teacher.username if class_obj.teacher else "担当教師",
                'student_count': len(class_obj.students) if hasattr(class_obj, 'students') else 0,
                'subject': class_obj.subject.name if class_obj.subject else "一般"
            }
            
            # カリキュラム設定の準備
            curriculum_settings = {
                'total_classes': data.get('total_classes', 35),
                'total_hours': data.get('total_hours', 29.2),
                'difficulty_level': data.get('difficulty_level', 2),
                'mastery_threshold': data.get('mastery_threshold', 80),
                'self_paced_mode': data.get('self_paced_mode', 'flexible'),
                'prerequisite_skills': data.get('prerequisite_skills', ''),
                'has_fieldwork': data.get('has_fieldwork', False),
                'fieldwork_count': data.get('fieldwork_count', 0),
                'has_presentation': data.get('has_presentation', True),
                'presentation_format': data.get('presentation_format', 'プレゼンテーション'),
                'group_work_level': data.get('group_work_level', 'ハイブリッド'),
                'external_collaboration': data.get('external_collaboration', False)
            }
            
            # タスク設定の準備
            task_settings = {
                'include_detailed_tasks': True,
                'default_task_types': data.get('default_task_types', ['worksheet', 'report']),
                'submission_formats': data.get('submission_formats', ['document']),
                'tasks_per_week': data.get('tasks_per_week', 3),
                'task_difficulty_distribution': data.get('task_difficulty_distribution', 'mixed'),
                'auto_generate_rubrics': data.get('auto_generate_rubrics', False),
                'enable_auto_approval': data.get('enable_auto_approval', False),
                'ai_generate_tasks': data.get('ai_generate_tasks', True),
                'task_generation_prompt': data.get('task_generation_prompt', '')
            }
            
            # 課題統合カリキュラムを生成（将来実装）
            # TODO: generate_curriculum_with_tasks関数の実装
            logger.info("Detailed task generation requested - using fallback for now")
            
            # 既存の標準生成を使用（暫定）
            return self._generate_standard_curriculum(class_obj, data)
            
        except Exception as e:
            logger.error(f"Error generating detailed curriculum: {str(e)}")
            return self._create_fallback_curriculum(class_obj, data)

    def _generate_standard_curriculum(self, class_obj: Class, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        標準カリキュラムを生成
        
        Args:
            class_obj: クラスオブジェクト
            data: 正規化されたデータ
            
        Returns:
            Dict: 生成結果
        """
        try:
            # 既存のAI生成機能を使用
            curriculum_content = generate_curriculum_with_ai(data)
            
            return {
                "success": True,
                "curriculum_content": curriculum_content,
                "generation_type": "standard_ai",
                "message": "AIによるカリキュラム生成が完了しました"
            }
            
        except Exception as e:
            logger.error(f"Error in standard AI generation: {str(e)}")
            return self._create_fallback_curriculum(class_obj, data)

    def _create_fallback_curriculum(self, class_obj: Class, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        フォールバックカリキュラムを作成
        
        Args:
            class_obj: クラスオブジェクト
            data: データ
            
        Returns:
            Dict: フォールバック結果
        """
        try:
            # 基本的なカリキュラム構造を作成
            basic_content = self._create_basic_curriculum_structure(class_obj, data)
            
            curriculum_content = {
                "title": data.get("title", f"{class_obj.name}のカリキュラム"),
                "description": data.get("description", f"{class_obj.name}の基本カリキュラム"),
                "content": json.dumps(basic_content, ensure_ascii=False),
                "format": "json"
            }
            
            return {
                "success": True,
                "curriculum_content": curriculum_content,
                "generation_type": "fallback",
                "message": "基本カリキュラムが生成されました（AI機能は一時的に利用できません）"
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback curriculum: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム生成中にエラーが発生しました: {str(e)}"
            }

    def _create_basic_curriculum_structure(self, class_obj: Class, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基本的なカリキュラム構造を作成
        
        Args:
            class_obj: クラスオブジェクト
            data: データ
            
        Returns:
            Dict: 基本カリキュラム構造
        """
        total_classes = data.get("total_classes", 35)
        subject_name = class_obj.subject.name if class_obj.subject else "一般"
        
        # 基本的な学習段階
        phases = [
            {"name": "基礎理解", "classes": int(total_classes * 0.3), "description": f"{subject_name}の基本概念を学習"},
            {"name": "応用学習", "classes": int(total_classes * 0.4), "description": f"{subject_name}の応用問題を解決"},
            {"name": "発展探究", "classes": int(total_classes * 0.3), "description": f"{subject_name}の発展的な内容を探究"}
        ]
        
        # フィールドワークの追加
        if data.get("has_fieldwork"):
            phases.append({
                "name": "フィールドワーク",
                "classes": data.get("fieldwork_count", 2),
                "description": "実地調査・体験学習"
            })
        
        # プレゼンテーションの追加
        if data.get("has_presentation"):
            phases.append({
                "name": "成果発表",
                "classes": 2,
                "description": f"{data.get('presentation_format', 'プレゼンテーション')}による学習成果の発表"
            })
        
        return {
            "phases": phases,
            "settings": {
                "difficulty_level": data.get("difficulty_level", 2),
                "mastery_threshold": data.get("mastery_threshold", 80),
                "self_paced_mode": data.get("self_paced_mode", "flexible"),
                "group_work_level": data.get("group_work_level", "ハイブリッド")
            },
            "metadata": {
                "generated_by": "QuestEd_Fallback",
                "version": "1.0",
                "total_classes": total_classes,
                "estimated_hours": data.get("total_hours", 29.2)
            }
        }