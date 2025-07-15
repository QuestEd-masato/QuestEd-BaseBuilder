# task_curriculum_helpers.py
"""
課題統合カリキュラム生成機能
================================
Week 2: AIプロンプト拡張

既存のカリキュラム生成システムとは完全に分離された、
週次課題を含むカリキュラム生成専用モジュール

安全性:
- 既存システムへの影響ゼロ
- エラー時は既存システムへフォールバック
- 完全にオプション機能として実装
"""

import json
import os
import re
from typing import Dict, Any, Optional


def generate_curriculum_with_tasks(class_details: Dict[str, Any], 
                                 curriculum_settings: Dict[str, Any],
                                 task_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    課題を含むカリキュラムをAIで生成する
    
    既存の generate_curriculum_with_ai とは完全分離された新機能
    
    Args:
        class_details: クラス情報（名前、大テーマ等）
        curriculum_settings: カリキュラム設定（時間数、活動等）  
        task_settings: 課題設定（オプション、None時は課題生成しない）
        
    Returns:
        dict: 課題を含むカリキュラム内容
        
    Note:
        task_settings が None の場合は、既存システムと同じ動作
    """
    
    # 課題設定が無い場合は、既存システムにフォールバック
    if not task_settings or not task_settings.get('include_detailed_tasks', False):
        # 既存のカリキュラム生成関数を呼び出し
        from .curriculum_helpers import generate_curriculum_with_ai
        return generate_curriculum_with_ai(class_details, curriculum_settings)
    
    try:
        # 拡張されたシステムプロンプトの構築
        system_prompt = _build_enhanced_system_prompt(task_settings)
        
        # 拡張されたユーザープロンプトの構築
        user_prompt = _build_enhanced_user_prompt(class_details, curriculum_settings, task_settings)
        
        # AI API呼び出し
        api_response = _call_openai_api(system_prompt, user_prompt)
        
        # レスポンス解析
        curriculum_data = _parse_ai_response(api_response)
        
        # データ検証
        validated_data = _validate_curriculum_data(curriculum_data)
        
        return validated_data
        
    except Exception as e:
        print(f"[WARNING] 課題統合カリキュラム生成エラー: {str(e)}")
        print("[INFO] 既存システムにフォールバックします")
        
        # エラー時は既存システムにフォールバック
        from .curriculum_helpers import generate_curriculum_with_ai
        return generate_curriculum_with_ai(class_details, curriculum_settings)


def _build_enhanced_system_prompt(task_settings: Dict[str, Any]) -> str:
    """拡張されたシステムプロンプトを構築"""
    
    # 基本プロンプト（既存システムと同じ）
    base_prompt = """
    あなたは探究学習のカリキュラム設計専門AIアシスタントです。
    教師が入力した条件に基づいて、クラスの大テーマに沿った探究学習カリキュラムを作成してください。
    
    カリキュラムは以下の点を考慮して設計してください：
    1. 探究のプロセス（問いの設定→情報収集→整理・分析→まとめ・表現）を意識した流れ
    2. 生徒の主体性を引き出す活動設計
    3. 指定された時間数内で実現可能な計画
    4. フィールドワークや発表会などの特別活動の適切な配置
    5. 評価方法として活動記録とルーブリック評価を基本とする
    """
    
    # 課題設計要件の追加
    task_prompt_extension = f"""
    
    ** 週次課題設計要件 **
    今回は各週の詳細な課題も設計してください：
    
    基本設定:
    - 主要課題タイプ: {', '.join(task_settings.get('default_task_types', ['worksheet', 'report']))}
    - 提出形式: {', '.join(task_settings.get('submission_formats', ['document']))}
    - 週あたり課題数: {task_settings.get('tasks_per_week', 3)}個
    - ルーブリック自動生成: {'有効' if task_settings.get('auto_generate_rubrics', False) else '無効'}
    - 自動承認機能: {'有効' if task_settings.get('enable_auto_approval', False) else '無効'}
    
    各週の課題設計要件:
    1. 課題は学習目標と直結させる
    2. 段階的難易度上昇を考慮（週を追うごとに複雑化）
    3. 多様な評価方法を組み合わせ
    4. 実践的な応用課題を含める
    5. 提出期限は週内で適切に分散
    6. 推定所要時間は50分授業を基準とする
    
    各課題に含める情報:
    - 明確なタイトルと詳細説明
    - 推定所要時間（分単位、30-90分の範囲）
    - 具体的な提出要件（文字数、形式、必須要素）
    - 5段階評価のルーブリック（excellent/good/satisfactory/needs_improvement/insufficient）
    - 教師指導のポイント・注意事項
    - 学習リソースや参考資料
    - 期限設定（週開始から何日後）
    """
    
    # 特別要求の追加
    if task_settings.get('task_generation_prompt'):
        task_prompt_extension += f"""
        
    特別要求: {task_settings['task_generation_prompt']}
        """
    
    # JSON出力形式の指定
    json_format = """
    
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
              "evaluation": "評価方法や観点",
              "tasks": [
                {
                  "title": "課題タイトル",
                  "type": "worksheet|report|presentation|discussion|project|test",
                  "description": "課題の詳細説明（200-300文字）",
                  "estimated_minutes": 30-90,
                  "difficulty_level": 1-5,
                  "submission_requirements": {
                    "format": "document|handwritten|video|presentation",
                    "min_word_count": 最小文字数,
                    "required_elements": ["必須要素1", "必須要素2"],
                    "file_types": ["許可するファイル形式"]
                  },
                  "evaluation_criteria": {
                    "criterion1": {
                      "excellent": 5,
                      "good": 4, 
                      "satisfactory": 3,
                      "needs_improvement": 2,
                      "insufficient": 1,
                      "description": "評価基準の説明"
                    },
                    "criterion2": { /* 同様の構造 */ }
                  },
                  "due_date_offset_days": 3-7,
                  "is_required": true|false,
                  "resources": ["参考資料1", "参考資料2"],
                  "teacher_notes": "教師向けの指導ポイント",
                  "auto_approval_enabled": true|false,
                  "auto_approval_threshold": 80
                }
              ]
            }
          ]
        }
      ],
      "rubric_suggestion": [
        {
          "category": "評価カテゴリ",
          "description": "カテゴリの説明",
          "levels": [
            {
              "level": "S/A/B/C",
              "description": "達成基準"
            }
          ]
        }
      ]
    }
    """
    
    return base_prompt + task_prompt_extension + json_format


def _build_enhanced_user_prompt(class_details: Dict[str, Any], 
                              curriculum_settings: Dict[str, Any],
                              task_settings: Dict[str, Any]) -> str:
    """拡張されたユーザープロンプトを構築"""
    
    # 基本情報（既存システムと同じ）
    base_info = f"""
    【クラス情報】
    クラス名：{class_details['name']}
    大テーマ：{class_details['main_theme']}
    大テーマの説明：{class_details['main_theme_description']}
    
    【カリキュラム設定】
    総時間数：{curriculum_settings['total_hours']}時間
    フィールドワーク：{'あり（' + str(curriculum_settings['fieldwork_count']) + '回）' if curriculum_settings['has_fieldwork'] else 'なし'}
    発表会：{'あり（形式：' + curriculum_settings['presentation_format'] + '）' if curriculum_settings['has_presentation'] else 'なし'}
    グループ活動の度合い：{curriculum_settings['group_work_level']}
    外部連携：{'あり' if curriculum_settings['external_collaboration'] else 'なし'}
    """
    
    # 課題設計情報の追加
    task_info = f"""
    
    【課題設計設定】
    詳細課題設計：有効
    主要課題タイプ：{', '.join(task_settings.get('default_task_types', []))}
    提出形式：{', '.join(task_settings.get('submission_formats', []))}
    週あたり課題数：{task_settings.get('tasks_per_week', 3)}個
    課題難易度配分：{task_settings.get('task_difficulty_distribution', 'mixed')}
    自動ルーブリック生成：{'有効' if task_settings.get('auto_generate_rubrics', False) else '無効'}
    自動承認機能：{'有効' if task_settings.get('enable_auto_approval', False) else '無効'}
    """
    
    if task_settings.get('task_generation_prompt'):
        task_info += f"""
    課題生成特別要求：{task_settings['task_generation_prompt']}
        """
    
    conclusion = """
    
    以上の条件に基づいて、週次の詳細課題を含む年間探究学習カリキュラムを作成してください。
    各週の課題は学習目標と連動し、段階的に難易度を上げ、多様な評価方法を組み合わせてください。
    """
    
    return base_info + task_info + conclusion


def _call_openai_api(system_prompt: str, user_prompt: str) -> str:
    """OpenAI APIを呼び出し（既存システムと同じロジック）"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY が設定されていません")
    
    # 新しいAPIスタイルを試す
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,  # 課題データのために増量
        )
        
        return response.choices[0].message.content
        
    except (ImportError, AttributeError):
        # 古いAPIスタイルにフォールバック
        import openai
        
        openai.api_key = api_key
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        
        return response.choices[0].message["content"]


def _parse_ai_response(content: str) -> Dict[str, Any]:
    """AI APIレスポンスを解析（既存システムと同じロジック）"""
    
    # 直接JSONとして解析を試みる
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # ```json ブロックから抽出
    json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # JSON パターンマッチング
    json_pattern = r"{[\s\S]*}"
    match = re.search(json_pattern, content)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    raise ValueError("有効なJSONデータを抽出できませんでした")


def _validate_curriculum_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """カリキュラムデータの検証と補完"""
    
    # 基本構造の確認
    if 'phases' not in data:
        raise ValueError("phases フィールドが見つかりません")
    
    # 各フェーズの検証
    for phase in data['phases']:
        if 'weeks' not in phase:
            continue
            
        for week in phase['weeks']:
            # 課題データの検証と補完
            if 'tasks' in week:
                week['tasks'] = _validate_tasks(week['tasks'])
    
    # rubric_suggestion の補完
    if 'rubric_suggestion' not in data:
        data['rubric_suggestion'] = _get_default_rubric()
    
    return data


def _validate_tasks(tasks: list) -> list:
    """課題データの検証と補完"""
    
    validated_tasks = []
    
    for task in tasks:
        # 必須フィールドの確認・補完
        validated_task = {
            'title': task.get('title', '未設定課題'),
            'type': task.get('type', 'worksheet'),
            'description': task.get('description', ''),
            'estimated_minutes': max(30, min(90, task.get('estimated_minutes', 50))),
            'difficulty_level': max(1, min(5, task.get('difficulty_level', 2))),
            'is_required': task.get('is_required', True),
            'due_date_offset_days': max(1, min(7, task.get('due_date_offset_days', 3))),
            'auto_approval_enabled': task.get('auto_approval_enabled', False),
            'auto_approval_threshold': max(60, min(100, task.get('auto_approval_threshold', 80))),
        }
        
        # submission_requirements の検証
        if 'submission_requirements' in task:
            validated_task['submission_requirements'] = _validate_submission_requirements(task['submission_requirements'])
        else:
            validated_task['submission_requirements'] = {
                'format': 'document',
                'min_word_count': 200,
                'required_elements': ['内容', '考察'],
                'file_types': ['pdf', 'docx', 'txt']
            }
        
        # evaluation_criteria の検証
        if 'evaluation_criteria' in task:
            validated_task['evaluation_criteria'] = _validate_evaluation_criteria(task['evaluation_criteria'])
        else:
            validated_task['evaluation_criteria'] = _get_default_evaluation_criteria()
        
        # その他のフィールド
        validated_task['resources'] = task.get('resources', [])
        validated_task['teacher_notes'] = task.get('teacher_notes', '')
        
        validated_tasks.append(validated_task)
    
    return validated_tasks


def _validate_submission_requirements(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """提出要件の検証"""
    
    valid_formats = ['document', 'handwritten', 'video', 'presentation']
    
    return {
        'format': requirements.get('format', 'document') if requirements.get('format') in valid_formats else 'document',
        'min_word_count': max(50, min(2000, requirements.get('min_word_count', 200))),
        'required_elements': requirements.get('required_elements', ['内容', '考察']),
        'file_types': requirements.get('file_types', ['pdf', 'docx', 'txt'])
    }


def _validate_evaluation_criteria(criteria: Dict[str, Any]) -> Dict[str, Any]:
    """評価基準の検証"""
    
    validated_criteria = {}
    
    for criterion_name, criterion_data in criteria.items():
        if isinstance(criterion_data, dict):
            validated_criteria[criterion_name] = {
                'excellent': criterion_data.get('excellent', 5),
                'good': criterion_data.get('good', 4),
                'satisfactory': criterion_data.get('satisfactory', 3),
                'needs_improvement': criterion_data.get('needs_improvement', 2),
                'insufficient': criterion_data.get('insufficient', 1),
                'description': criterion_data.get('description', f'{criterion_name}の評価基準')
            }
    
    # 空の場合はデフォルトを設定
    if not validated_criteria:
        validated_criteria = _get_default_evaluation_criteria()
    
    return validated_criteria


def _get_default_evaluation_criteria() -> Dict[str, Any]:
    """デフォルト評価基準"""
    
    return {
        '内容の適切性': {
            'excellent': 5,
            'good': 4,
            'satisfactory': 3,
            'needs_improvement': 2,
            'insufficient': 1,
            'description': '課題の要求に対する内容の適切性'
        },
        '論理性・構成': {
            'excellent': 5,
            'good': 4,
            'satisfactory': 3,
            'needs_improvement': 2,
            'insufficient': 1,
            'description': '論理的な構成と分かりやすい表現'
        }
    }


def _get_default_rubric() -> list:
    """デフォルトルーブリック"""
    
    return [
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
    ]


# 課題データ専用のユーティリティ関数
def extract_tasks_from_curriculum(curriculum_data: Dict[str, Any]) -> list:
    """カリキュラムデータから課題一覧を抽出"""
    
    tasks = []
    
    for phase in curriculum_data.get('phases', []):
        for week in phase.get('weeks', []):
            if 'tasks' in week:
                for task in week['tasks']:
                    task_with_context = task.copy()
                    task_with_context['phase'] = phase.get('phase', '')
                    task_with_context['week'] = week.get('week', '')
                    task_with_context['week_theme'] = week.get('theme', '')
                    tasks.append(task_with_context)
    
    return tasks


def get_task_statistics(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
    """課題統計の計算"""
    
    tasks = extract_tasks_from_curriculum(curriculum_data)
    
    if not tasks:
        return {
            'total_tasks': 0,
            'total_estimated_time': 0,
            'required_tasks': 0,
            'optional_tasks': 0,
            'task_types': {},
            'difficulty_distribution': {}
        }
    
    # 基本統計
    total_tasks = len(tasks)
    total_estimated_time = sum(task.get('estimated_minutes', 50) for task in tasks)
    required_tasks = sum(1 for task in tasks if task.get('is_required', True))
    optional_tasks = total_tasks - required_tasks
    
    # タイプ別統計
    task_types = {}
    for task in tasks:
        task_type = task.get('type', 'unknown')
        task_types[task_type] = task_types.get(task_type, 0) + 1
    
    # 難易度分布
    difficulty_distribution = {}
    for task in tasks:
        difficulty = task.get('difficulty_level', 2)
        difficulty_distribution[f'level_{difficulty}'] = difficulty_distribution.get(f'level_{difficulty}', 0) + 1
    
    return {
        'total_tasks': total_tasks,
        'total_estimated_time': total_estimated_time,
        'required_tasks': required_tasks,
        'optional_tasks': optional_tasks,
        'task_types': task_types,
        'difficulty_distribution': difficulty_distribution
    }