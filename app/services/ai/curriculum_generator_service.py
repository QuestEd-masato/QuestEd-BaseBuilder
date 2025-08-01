"""
カリキュラム生成サービス（メイン）
Phase 7-3: curriculum_helpers.py のメイン機能をサービス化
"""

import logging
from typing import Dict, Any, Optional

from app.services.base_service import BaseService
from .openai_client_service import OpenAIClientService
from .prompt_builder_service import PromptBuilderService
from .response_parser_service import ResponseParserService
from .curriculum_formatter_service import CurriculumFormatterService

logger = logging.getLogger(__name__)


class CurriculumGeneratorService(BaseService):
    """カリキュラム生成メインサービス
    
    Phase 7-3: curriculum_helpers.py から分離
    他のサービスを統合してカリキュラム生成のワークフローを制御
    """
    
    def __init__(self):
        super().__init__()
        # 各専門サービスを初期化
        self.openai_client = OpenAIClientService()
        self.prompt_builder = PromptBuilderService()
        self.response_parser = ResponseParserService()
        self.formatter = CurriculumFormatterService()
    
    def generate_with_lessons(
        self,
        class_details: Dict[str, Any],
        curriculum_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        レッスン形式カリキュラム生成
        
        Args:
            class_details: クラスに関する情報（名前、大テーマなど）
            curriculum_settings: カリキュラム設定（時間数、フィールドワーク有無など）
            
        Returns:
            dict: レッスン形式カリキュラム内容
        """
        try:
            logger.info("Starting lesson-based curriculum generation")
            
            # 1. プロンプトの構築
            system_prompt = self.prompt_builder.build_lesson_system_prompt()
            user_prompt = self.prompt_builder.build_lesson_user_prompt(
                class_details, curriculum_settings
            )
            
            # 2. API呼び出し
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response_content = self.openai_client.call_chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.7,
                max_tokens=4000
            )
            
            # 3. レスポンスの解析
            curriculum_data = self.response_parser.parse_curriculum_response(
                response_content,
                response_type='lesson'
            )
            
            logger.info("Lesson-based curriculum generation completed successfully")
            return curriculum_data
            
        except Exception as e:
            logger.error(f"Error generating lesson-based curriculum: {str(e)}")
            # エラー時はデフォルトテンプレートを返す
            return self.response_parser._get_default_template('lesson')
    
    def generate_traditional(
        self,
        class_details: Dict[str, Any],
        curriculum_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        従来形式カリキュラム生成（互換性のため）
        
        Args:
            class_details: クラスに関する情報
            curriculum_settings: カリキュラム設定
            
        Returns:
            dict: 従来形式カリキュラム内容
        """
        try:
            logger.info("Starting traditional curriculum generation")
            
            # 1. プロンプトの構築
            system_prompt = self.prompt_builder.build_traditional_system_prompt()
            user_prompt = self.prompt_builder.build_traditional_user_prompt(
                class_details, curriculum_settings
            )
            
            # 2. API呼び出し
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response_content = self.openai_client.call_chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.7,
                max_tokens=3000
            )
            
            # 3. レスポンスの解析
            curriculum_data = self.response_parser.parse_curriculum_response(
                response_content,
                response_type='traditional'
            )
            
            logger.info("Traditional curriculum generation completed successfully")
            return curriculum_data
            
        except Exception as e:
            logger.error(f"Error generating traditional curriculum: {str(e)}")
            # エラー時はデフォルトテンプレートを返す
            return self.response_parser._get_default_template('traditional')
    
    def generate_csv(self, curriculum_data: Dict[str, Any]) -> str:
        """
        カリキュラムデータをCSV形式に変換
        
        Args:
            curriculum_data: JSON形式のカリキュラムデータ
            
        Returns:
            str: CSV形式のカリキュラムデータ
        """
        try:
            return self.formatter.to_csv(curriculum_data)
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}")
            return ""
    
    def validate_api_key(self) -> bool:
        """APIキーが設定されているか確認"""
        return self.openai_client.is_available()
    
    def estimate_generation_cost(
        self,
        class_details: Dict[str, Any],
        curriculum_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成コストを概算（将来の拡張用）"""
        try:
            # プロンプトを構築してトークン数を概算
            system_prompt = self.prompt_builder.build_lesson_system_prompt()
            user_prompt = self.prompt_builder.build_lesson_user_prompt(
                class_details, curriculum_settings
            )
            
            total_prompt = system_prompt + user_prompt
            estimated_tokens = self.openai_client.estimate_tokens(total_prompt)
            
            # 概算コストを計算（GPT-4の料金を仮定）
            # 入力: $0.03/1K tokens, 出力: $0.06/1K tokens
            input_cost = (estimated_tokens / 1000) * 0.03
            output_cost = (4000 / 1000) * 0.06  # 最大出力トークン数で計算
            
            return {
                "estimated_input_tokens": estimated_tokens,
                "estimated_output_tokens": 4000,
                "estimated_cost_usd": round(input_cost + output_cost, 2)
            }
            
        except Exception as e:
            logger.error(f"Error estimating cost: {str(e)}")
            return {
                "error": str(e)
            }