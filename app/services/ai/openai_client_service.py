"""
OpenAI API通信サービス
Phase 7-3: curriculum_helpers.py から API通信機能を分離
"""

import os
import logging
from typing import Dict, List, Optional, Any
import json
import time

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class OpenAIClientService(BaseService):
    """OpenAI API通信専門サービス
    
    Phase 7-3: curriculum_helpers.py から分離
    Single Responsibility: OpenAI APIとの通信のみを担当
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._client = None
        self._client_type = None  # 'new' or 'legacy'
        self._initialize_client()
    
    def _initialize_client(self):
        """OpenAIクライアントの初期化（新旧API両対応）"""
        try:
            # 新しいAPIスタイルを試す
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
            self._client_type = 'new'
            logger.info("OpenAI client initialized with new API style")
        except (ImportError, AttributeError):
            # 古いAPIスタイルにフォールバック
            try:
                import openai
                openai.api_key = self.api_key
                self._client = openai
                self._client_type = 'legacy'
                logger.info("OpenAI client initialized with legacy API style")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                raise
    
    def call_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """
        ChatGPT APIを呼び出す
        
        Args:
            messages: チャットメッセージのリスト
            model: 使用するモデル名
            temperature: 生成の多様性（0-1）
            max_tokens: 最大トークン数
            retry_count: リトライ回数
            retry_delay: リトライ間隔（秒）
            
        Returns:
            str: APIレスポンスのコンテンツ
            
        Raises:
            Exception: API呼び出しに失敗した場合
        """
        if not self.api_key:
            raise ValueError("OpenAI API key is not set")
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"Calling OpenAI API (attempt {attempt + 1}/{retry_count})")
                
                if self._client_type == 'new':
                    # 新しいAPIスタイル
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    content = response.choices[0].message.content
                else:
                    # 古いAPIスタイル
                    response = self._client.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    content = response.choices[0].message["content"]
                
                logger.debug(f"API call successful, response length: {len(content)}")
                return content
                
            except Exception as e:
                logger.warning(f"API call attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < retry_count - 1:
                    time.sleep(retry_delay * (attempt + 1))  # 指数バックオフ
                else:
                    logger.error(f"All API call attempts failed: {str(e)}")
                    raise
    
    def is_available(self) -> bool:
        """APIが利用可能かチェック"""
        return bool(self.api_key and self._client)
    
    def get_model_list(self) -> List[str]:
        """利用可能なモデルのリストを取得"""
        # 現在はハードコードだが、将来的にはAPIから取得可能
        return ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"]
    
    def estimate_tokens(self, text: str) -> int:
        """テキストのトークン数を概算"""
        # 簡易的な概算（実際のトークナイザーを使用することも可能）
        # 日本語は1文字≒1トークン、英語は4文字≒1トークンとして概算
        japanese_chars = sum(1 for c in text if ord(c) > 0x3000)
        english_chars = len(text) - japanese_chars
        return japanese_chars + (english_chars // 4)
    
    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        """メッセージフォーマットの検証"""
        if not messages:
            return False
        
        for message in messages:
            if not isinstance(message, dict):
                return False
            if 'role' not in message or 'content' not in message:
                return False
            if message['role'] not in ['system', 'user', 'assistant']:
                return False
        
        return True