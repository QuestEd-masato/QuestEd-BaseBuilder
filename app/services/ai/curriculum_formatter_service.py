"""
カリキュラムフォーマット変換サービス
Phase 7-3: curriculum_helpers.py からCSV生成機能を分離
"""

import csv
import io
import logging
from typing import Dict, Any, List, Optional

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class CurriculumFormatterService(BaseService):
    """フォーマット変換専門サービス
    
    Phase 7-3: curriculum_helpers.py から分離
    Single Responsibility: カリキュラムデータのフォーマット変換のみを担当
    """
    
    def __init__(self):
        super().__init__()
    
    def to_csv(self, curriculum_data: Dict[str, Any]) -> str:
        """
        カリキュラムデータをCSV形式に変換する
        
        Args:
            curriculum_data: JSON形式のカリキュラムデータ
            
        Returns:
            str: CSV形式のカリキュラムデータ
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\n")  # 改行コードを明示的に指定
            
            # データタイプを判定
            if 'lessons' in curriculum_data:
                self._write_lesson_format_csv(writer, curriculum_data)
            elif 'phases' in curriculum_data:
                self._write_traditional_format_csv(writer, curriculum_data)
            else:
                logger.warning("Unknown curriculum data format")
                return ""
            
            csv_content = output.getvalue()
            logger.debug(f"Generated CSV with {len(csv_content)} characters")
            return csv_content
            
        except Exception as e:
            logger.error(f"Error converting curriculum to CSV: {str(e)}")
            return ""
    
    def _write_lesson_format_csv(self, writer: csv.writer, curriculum_data: Dict[str, Any]):
        """レッスン形式のCSVを書き込む"""
        # ヘッダー行
        writer.writerow([
            "レッスン番号", "レッスンタイトル", "レッスンタイプ", 
            "時間（分）", "説明", "学習目標", "タスク"
        ])
        
        # レッスンデータの書き込み
        for lesson in curriculum_data.get("lessons", []):
            # 学習目標を文字列に変換
            objectives = "; ".join(lesson.get("learning_objectives", []))
            
            # タスクを文字列に変換
            tasks = []
            for task in lesson.get("tasks", []):
                task_str = f"{task.get('task_number', '')}. {task.get('title', '')}: {task.get('description', '')}"
                tasks.append(task_str)
            tasks_str = "; ".join(tasks)
            
            writer.writerow([
                lesson.get("lesson_number", ""),
                lesson.get("title", ""),
                lesson.get("lesson_type", ""),
                lesson.get("duration_minutes", ""),
                lesson.get("description", ""),
                objectives,
                tasks_str
            ])
        
        # ルーブリックデータの追加
        self._write_rubric_data(writer, curriculum_data)
    
    def _write_traditional_format_csv(self, writer: csv.writer, curriculum_data: Dict[str, Any]):
        """従来形式のCSVを書き込む"""
        # ヘッダー行
        writer.writerow([
            "フェーズ", "週", "時間数", "テーマ", 
            "活動内容", "教師のサポート", "評価方法"
        ])
        
        # カリキュラムデータの書き込み
        for phase in curriculum_data.get("phases", []):
            phase_name = phase.get("phase", "")
            for week in phase.get("weeks", []):
                writer.writerow([
                    phase_name,
                    week.get("week", ""),
                    week.get("hours", ""),
                    week.get("theme", ""),
                    week.get("activities", ""),
                    week.get("teacher_support", ""),
                    week.get("evaluation", ""),
                ])
        
        # ルーブリックデータの追加
        self._write_rubric_data(writer, curriculum_data)
    
    def _write_rubric_data(self, writer: csv.writer, curriculum_data: Dict[str, Any]):
        """ルーブリックデータを書き込む"""
        # ルーブリックデータのための区切り
        writer.writerow([])
        writer.writerow(["ルーブリック評価項目"])
        writer.writerow(["カテゴリ", "説明", "レベル", "達成基準"])
        
        # ルーブリックデータの書き込み
        for rubric in curriculum_data.get("rubric_suggestion", []):
            category = rubric.get("category", "")
            description = rubric.get("description", "")
            for level in rubric.get("levels", []):
                writer.writerow([
                    category,
                    description,
                    level.get("level", ""),
                    level.get("description", ""),
                ])
    
    def to_html_table(self, curriculum_data: Dict[str, Any]) -> str:
        """カリキュラムデータをHTMLテーブル形式に変換（将来の拡張用）"""
        # 実装予定
        pass
    
    def to_markdown(self, curriculum_data: Dict[str, Any]) -> str:
        """カリキュラムデータをMarkdown形式に変換（将来の拡張用）"""
        # 実装予定
        pass
    
    def validate_format(self, data: Any, format_type: str) -> bool:
        """データフォーマットの検証"""
        if format_type == 'csv':
            return isinstance(data, str)
        elif format_type == 'json':
            return isinstance(data, dict)
        else:
            return False