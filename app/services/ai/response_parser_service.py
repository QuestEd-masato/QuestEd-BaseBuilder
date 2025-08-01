"""
レスポンス解析サービス
Phase 7-3: curriculum_helpers.py からJSON解析機能を分離
"""

import json
import re
import logging
from typing import Dict, Any, Optional

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ResponseParserService(BaseService):
    """レスポンス解析専門サービス
    
    Phase 7-3: curriculum_helpers.py から分離
    Single Responsibility: APIレスポンスの解析のみを担当
    """
    
    def __init__(self):
        super().__init__()
        self._init_default_templates()
    
    def _init_default_templates(self):
        """デフォルトテンプレートの初期化"""
        self.default_lesson_template = {
            "lessons": [
                {
                    "lesson_number": 1,
                    "title": "オリエンテーション",
                    "lesson_type": "lecture",
                    "duration_minutes": 50,
                    "description": "探究学習の概要説明、大テーマの理解",
                    "learning_objectives": ["探究学習の意義を理解する"],
                    "tasks": [
                        {
                            "task_number": 1,
                            "title": "探究テーマの理解",
                            "description": "大テーマについて調べ、自分の興味を明確にする"
                        }
                    ]
                }
            ],
            "rubric_suggestion": [
                {
                    "category": "問いの設定",
                    "description": "探究の問いを設定する力",
                    "levels": [
                        {"level": "S", "description": "独創的で深い問いを設定できる"},
                        {"level": "A", "description": "適切な問いを設定できる"},
                        {"level": "B", "description": "基本的な問いを設定できる"},
                        {"level": "C", "description": "問いの設定が不十分"},
                    ],
                }
            ],
        }
        
        self.default_traditional_template = {
            "phases": [
                {
                    "phase": "準備期",
                    "weeks": [
                        {
                            "week": "第1週",
                            "hours": 2,
                            "theme": "オリエンテーション",
                            "activities": "探究学習の概要説明、大テーマの理解",
                            "teacher_support": "探究学習の意義と進め方を説明",
                            "evaluation": "活動記録の確認",
                        }
                    ],
                }
            ],
            "rubric_suggestion": [
                {
                    "category": "問いの設定",
                    "description": "探究の問いを設定する力",
                    "levels": [
                        {"level": "S", "description": "独創的で深い問いを設定できる"},
                        {"level": "A", "description": "適切な問いを設定できる"},
                        {"level": "B", "description": "基本的な問いを設定できる"},
                        {"level": "C", "description": "問いの設定が不十分"},
                    ],
                }
            ],
        }
    
    def parse_curriculum_response(
        self,
        content: str,
        response_type: str = 'lesson'
    ) -> Dict[str, Any]:
        """
        カリキュラムレスポンスを解析
        
        Args:
            content: APIレスポンスのコンテンツ
            response_type: 'lesson' または 'traditional'
            
        Returns:
            Dict[str, Any]: 解析されたカリキュラムデータ
        """
        try:
            logger.debug(f"Parsing response of type '{response_type}', length: {len(content)}")
            
            # 直接JSONとして解析を試みる
            try:
                curriculum_data = json.loads(content)
                logger.debug("Direct JSON parsing successful")
                return self._validate_curriculum_data(curriculum_data, response_type)
            except json.JSONDecodeError as e:
                logger.debug(f"Direct JSON parsing failed: {str(e)}")
            
            # コードブロック内のJSONを抽出
            json_str = self._extract_json_from_codeblock(content)
            if json_str:
                try:
                    curriculum_data = json.loads(json_str)
                    logger.debug("Codeblock JSON parsing successful")
                    return self._validate_curriculum_data(curriculum_data, response_type)
                except json.JSONDecodeError as e:
                    logger.debug(f"Codeblock JSON parsing failed: {str(e)}")
            
            # 最後の手段：JSONパターンを探して抽出
            json_str = self._extract_json_pattern(content)
            if json_str:
                try:
                    curriculum_data = json.loads(json_str)
                    logger.debug("Pattern JSON parsing successful")
                    return self._validate_curriculum_data(curriculum_data, response_type)
                except json.JSONDecodeError as e:
                    logger.debug(f"Pattern JSON parsing failed: {str(e)}")
            
            # すべての解析が失敗した場合
            logger.warning("All parsing attempts failed, returning default template")
            return self._get_default_template(response_type)
            
        except Exception as e:
            logger.error(f"Error parsing curriculum response: {str(e)}")
            return self._get_default_template(response_type)
    
    def _extract_json_from_codeblock(self, content: str) -> Optional[str]:
        """コードブロックからJSON部分を抽出"""
        # ```json ... ``` パターンを探す
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # ``` ... ``` パターンも試す
        code_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
        if code_match:
            potential_json = code_match.group(1).strip()
            # JSONっぽいかチェック
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json
        
        return None
    
    def _extract_json_pattern(self, content: str) -> Optional[str]:
        """テキストからJSONパターンを抽出"""
        # 最も外側の { } を見つける
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(json_pattern, content, re.DOTALL)
        
        # 最も長いマッチを選択（より完全なJSONの可能性が高い）
        longest_match = None
        longest_length = 0
        
        for match in matches:
            match_str = match.group(0)
            if len(match_str) > longest_length:
                longest_match = match_str
                longest_length = len(match_str)
        
        return longest_match
    
    def _validate_curriculum_data(
        self,
        data: Dict[str, Any],
        response_type: str
    ) -> Dict[str, Any]:
        """カリキュラムデータの検証"""
        try:
            if response_type == 'lesson':
                # レッスン形式の検証
                if 'lessons' not in data:
                    logger.warning("Missing 'lessons' key in data")
                    return self._get_default_template(response_type)
                
                # 最低限の構造チェック
                if not isinstance(data['lessons'], list):
                    logger.warning("'lessons' is not a list")
                    return self._get_default_template(response_type)
                
            else:  # traditional
                # 従来形式の検証
                if 'phases' not in data:
                    logger.warning("Missing 'phases' key in data")
                    return self._get_default_template(response_type)
                
                # 最低限の構造チェック
                if not isinstance(data['phases'], list):
                    logger.warning("'phases' is not a list")
                    return self._get_default_template(response_type)
            
            return data
            
        except Exception as e:
            logger.error(f"Error validating curriculum data: {str(e)}")
            return self._get_default_template(response_type)
    
    def _get_default_template(self, response_type: str) -> Dict[str, Any]:
        """デフォルトテンプレートを取得"""
        if response_type == 'lesson':
            return self.default_lesson_template.copy()
        else:
            return self.default_traditional_template.copy()
    
    def extract_error_message(self, content: str) -> Optional[str]:
        """エラーメッセージを抽出"""
        # エラーパターンを探す
        error_patterns = [
            r"error:\s*(.+)",
            r"Error:\s*(.+)",
            r"エラー：\s*(.+)",
            r"失敗：\s*(.+)"
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None