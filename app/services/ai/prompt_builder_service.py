"""
プロンプト構築サービス
Phase 7-3: curriculum_helpers.py からプロンプト構築機能を分離
"""

import logging
from typing import Dict, Any, Optional

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class PromptBuilderService(BaseService):
    """プロンプト構築専門サービス
    
    Phase 7-3: curriculum_helpers.py から分離
    Single Responsibility: AIプロンプトの構築のみを担当
    """
    
    def __init__(self):
        super().__init__()
        # プロンプトテンプレートを定義
        self._init_prompt_templates()
    
    def _init_prompt_templates(self):
        """プロンプトテンプレートの初期化"""
        self.lesson_system_prompt = """
あなたは探究学習のカリキュラム設計専門AIアシスタントです。
教師が入力した条件に基づいて、クラスの大テーマに沿ったレッスン形式の探究学習カリキュラムを作成してください。

カリキュラムは以下の点を考慮して設計してください：
1. 探究のプロセス（問いの設定→情報収集→整理・分析→まとめ・表現）を意識した流れ
2. 生徒の主体性を引き出す活動設計
3. 指定された時間数内で実現可能な計画
4. フィールドワークや発表会などの特別活動の適切な配置
5. 評価方法として活動記録とルーブリック評価を基本とする
6. レッスン形式で個別の授業とタスクを明確に分離する

出力はJSON形式で、以下の構造で提供してください：
{
  "lessons": [
    {
      "lesson_number": 1,
      "title": "レッスンタイトル",
      "lesson_type": "lecture|practice|discussion|presentation|experiment|review",
      "duration_minutes": 50,
      "description": "レッスンの詳細内容、目標、活動",
      "learning_objectives": ["学習目標"],
      "tasks": [
        {
          "task_number": 1,
          "title": "タスクタイトル",
          "description": "タスクの詳細説明"
        }
      ]
    }
  ],
  "rubric_suggestion": [
    {
      "category": "評価カテゴリ（例：問いの設定、情報収集、分析力）",
      "description": "このカテゴリの説明",
      "levels": [
        {
          "level": "S/A/B/C などの評価レベル",
          "description": "このレベルの達成基準"
        }
      ]
    }
  ]
}"""

        self.traditional_system_prompt = """
あなたは探究学習のカリキュラム設計専門AIアシスタントです。
教師が入力した条件に基づいて、クラスの大テーマに沿った探究学習カリキュラムを作成してください。

カリキュラムは以下の点を考慮して設計してください：
1. 探究のプロセス（問いの設定→情報収集→整理・分析→まとめ・表現）を意識した流れ
2. 生徒の主体性を引き出す活動設計
3. 指定された時間数内で実現可能な計画
4. フィールドワークや発表会などの特別活動の適切な配置
5. 評価方法として活動記録とルーブリック評価を基本とする

出力はJSON形式で、以下の構造で提供してください：
{
  "phases": [
    {
      "phase": "フェーズ名（例：準備期、探究前半、探究後半、まとめ）",
      "weeks": [
        {
          "week": "第X週",
          "hours": 時間数,
          "theme": "この週のテーマ",
          "activities": "具体的な活動内容",
          "teacher_support": "教師のサポート内容",
          "evaluation": "評価方法や観点"
        }
      ]
    }
  ],
  "rubric_suggestion": [
    {
      "category": "評価カテゴリ（例：問いの設定、情報収集、分析力）",
      "description": "このカテゴリの説明",
      "levels": [
        {
          "level": "S/A/B/C などの評価レベル",
          "description": "このレベルの達成基準"
        }
      ]
    }
  ]
}"""
    
    def build_lesson_system_prompt(self) -> str:
        """レッスン形式用システムプロンプト構築"""
        return self.lesson_system_prompt
    
    def build_traditional_system_prompt(self) -> str:
        """従来形式用システムプロンプト構築"""
        return self.traditional_system_prompt
    
    def build_lesson_user_prompt(
        self, 
        class_details: Dict[str, Any],
        curriculum_settings: Dict[str, Any]
    ) -> str:
        """レッスン形式用ユーザープロンプト構築"""
        try:
            # 必須パラメータの検証
            required_class_fields = ['name', 'main_theme', 'main_theme_description']
            for field in required_class_fields:
                if field not in class_details:
                    raise ValueError(f"Required field '{field}' missing in class_details")
            
            required_settings_fields = ['total_hours']
            for field in required_settings_fields:
                if field not in curriculum_settings:
                    raise ValueError(f"Required field '{field}' missing in curriculum_settings")
            
            # フィールドワーク情報の構築
            fieldwork_info = self._build_fieldwork_info(curriculum_settings)
            
            # 発表会情報の構築
            presentation_info = self._build_presentation_info(curriculum_settings)
            
            # グループ活動レベルの取得
            group_work_level = curriculum_settings.get('group_work_level', '中')
            
            # 外部連携情報の取得
            external_collaboration = 'あり' if curriculum_settings.get('external_collaboration', False) else 'なし'
            
            prompt = f"""【クラス情報】
クラス名：{class_details['name']}
大テーマ：{class_details['main_theme']}
大テーマの説明：{class_details['main_theme_description']}

【カリキュラム設定】
総時間数：{curriculum_settings['total_hours']}時間
フィールドワーク：{fieldwork_info}
発表会：{presentation_info}
グループ活動の度合い：{group_work_level}
外部連携：{external_collaboration}

以上の条件に基づいて、レッスン形式の探究学習カリキュラムを作成してください。
各レッスンは50分授業を基本とし、各レッスンに2-4個のタスクを含めてください。
総時間数に合わせてレッスン数を調整してください。"""
            
            logger.debug(f"Built user prompt: {len(prompt)} characters")
            return prompt
            
        except Exception as e:
            logger.error(f"Error building user prompt: {str(e)}")
            raise
    
    def build_traditional_user_prompt(
        self,
        class_details: Dict[str, Any],
        curriculum_settings: Dict[str, Any]
    ) -> str:
        """従来形式用ユーザープロンプト構築"""
        try:
            # レッスン形式と同じ検証ロジックを使用
            required_class_fields = ['name', 'main_theme', 'main_theme_description']
            for field in required_class_fields:
                if field not in class_details:
                    raise ValueError(f"Required field '{field}' missing in class_details")
            
            required_settings_fields = ['total_hours']
            for field in required_settings_fields:
                if field not in curriculum_settings:
                    raise ValueError(f"Required field '{field}' missing in curriculum_settings")
            
            # フィールドワーク情報の構築
            fieldwork_info = self._build_fieldwork_info(curriculum_settings)
            
            # 発表会情報の構築
            presentation_info = self._build_presentation_info(curriculum_settings)
            
            # グループ活動レベルの取得
            group_work_level = curriculum_settings.get('group_work_level', '中')
            
            # 外部連携情報の取得
            external_collaboration = 'あり' if curriculum_settings.get('external_collaboration', False) else 'なし'
            
            prompt = f"""【クラス情報】
クラス名：{class_details['name']}
大テーマ：{class_details['main_theme']}
大テーマの説明：{class_details['main_theme_description']}

【カリキュラム設定】
総時間数：{curriculum_settings['total_hours']}時間
フィールドワーク：{fieldwork_info}
発表会：{presentation_info}
グループ活動の度合い：{group_work_level}
外部連携：{external_collaboration}

以上の条件に基づいて、年間の探究学習カリキュラムを作成してください。"""
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error building traditional user prompt: {str(e)}")
            raise
    
    def _build_fieldwork_info(self, curriculum_settings: Dict[str, Any]) -> str:
        """フィールドワーク情報の構築"""
        if curriculum_settings.get('has_fieldwork', False):
            count = curriculum_settings.get('fieldwork_count', 1)
            return f'あり（{count}回）'
        else:
            return 'なし'
    
    def _build_presentation_info(self, curriculum_settings: Dict[str, Any]) -> str:
        """発表会情報の構築"""
        if curriculum_settings.get('has_presentation', False):
            format_type = curriculum_settings.get('presentation_format', 'ポスター')
            return f'あり（形式：{format_type}）'
        else:
            return 'なし'
    
    def validate_prompt_length(self, prompt: str, max_length: int = 10000) -> bool:
        """プロンプトの長さを検証"""
        return len(prompt) <= max_length