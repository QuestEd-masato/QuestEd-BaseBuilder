# -*- coding: utf-8 -*-
"""
CurriculumImportExportService

カリキュラムのインポート・エクスポート機能を管理する専門サービス
Phase8C: curriculum_management.pyから分離
"""
import csv
import io
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from flask import Response

from app.models import Curriculum, CurriculumUnit

logger = logging.getLogger(__name__)


class CurriculumImportExportService:
    """カリキュラム インポート・エクスポート専門サービス"""

    def export_curriculum_to_csv(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムをCSV形式でエクスポート
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: エクスポート結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            # CSVデータの作成
            csv_data = self._create_csv_data(curriculum)
            
            # CSVファイル名の生成
            filename = f"curriculum_{curriculum.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return {
                "success": True,
                "csv_data": csv_data,
                "filename": filename,
                "curriculum": curriculum
            }

        except Exception as e:
            logger.error(f"Error exporting curriculum {curriculum_id}: {str(e)}")
            return {
                "success": False,
                "message": f"エクスポート中にエラーが発生しました: {str(e)}"
            }

    def _create_csv_data(self, curriculum: Curriculum) -> str:
        """
        カリキュラムデータからCSVを生成
        
        Args:
            curriculum: カリキュラムオブジェクト
            
        Returns:
            str: CSV文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー行
        writer.writerow(['項目', '内容'])
        
        # 基本情報
        writer.writerow(['タイトル', curriculum.title])
        writer.writerow(['説明', curriculum.description or ''])
        writer.writerow(['総授業数', curriculum.total_classes])
        writer.writerow(['総時間数', curriculum.total_hours])
        writer.writerow(['難易度', curriculum.difficulty_level])
        writer.writerow(['自己ペースモード', curriculum.self_paced_mode])
        writer.writerow(['作成日', curriculum.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        
        # 単元情報
        units = CurriculumUnit.query.filter_by(
            curriculum_id=curriculum.id
        ).order_by(CurriculumUnit.order_index).all()
        
        if units:
            writer.writerow(['', ''])  # 空行
            writer.writerow(['単元一覧', ''])
            writer.writerow(['順序', 'タイトル', '説明', '期間（週）'])
            
            for unit in units:
                writer.writerow([
                    unit.order_index,
                    unit.title,
                    unit.description or '',
                    unit.duration_weeks or 1
                ])
        
        # ルーブリック情報（curriculum_dataから取得）
        if curriculum.curriculum_data:
            try:
                data = json.loads(curriculum.curriculum_data)
                rubric_info = data.get('rubric', {})
                evaluation_aspects = data.get('evaluation_aspects', {})
                
                if rubric_info or evaluation_aspects:
                    writer.writerow(['', ''])  # 空行
                    writer.writerow(['ルーブリック情報', ''])
                    
                    # 評価観点
                    if evaluation_aspects:
                        writer.writerow(['評価観点_知識技能', evaluation_aspects.get('knowledge', 30)])
                        writer.writerow(['評価観点_思考判断表現', evaluation_aspects.get('thinking', 40)])
                        writer.writerow(['評価観点_主体的態度', evaluation_aspects.get('attitude', 30)])
                    
                    # ルーブリック詳細
                    if rubric_info and isinstance(rubric_info, list):
                        writer.writerow(['', ''])
                        writer.writerow(['ルーブリック詳細', ''])
                        writer.writerow(['項目名', '説明', '優秀(A)', '良好(B)', '要改善(C)'])
                        
                        for item in rubric_info:
                            levels = item.get('levels', ['', '', ''])
                            writer.writerow([
                                item.get('category', ''),
                                item.get('description', ''),
                                levels[0] if len(levels) > 0 else '',
                                levels[1] if len(levels) > 1 else '',
                                levels[2] if len(levels) > 2 else ''
                            ])
            except json.JSONDecodeError:
                pass  # JSONデコードエラーは無視
        
        # カリキュラムコンテンツ
        if curriculum.content:
            writer.writerow(['', ''])  # 空行
            writer.writerow(['コンテンツ', curriculum.content])
        
        return output.getvalue()

    def import_curriculum_from_file(self, file_data: Any, file_type: str, class_id: int) -> Dict[str, Any]:
        """
        ファイルからカリキュラムをインポート
        
        Args:
            file_data: ファイルデータ
            file_type: ファイルタイプ ('csv' or 'json')
            class_id: クラスID
            
        Returns:
            Dict: インポート結果
        """
        try:
            if file_type.lower() == 'csv':
                return self._import_from_csv(file_data, class_id)
            elif file_type.lower() == 'json':
                return self._import_from_json(file_data, class_id)
            else:
                return {
                    "success": False,
                    "message": "サポートされていないファイル形式です"
                }

        except Exception as e:
            logger.error(f"Error importing curriculum: {str(e)}")
            return {
                "success": False,
                "message": f"インポート中にエラーが発生しました: {str(e)}"
            }

    def _import_from_csv(self, file_data: Any, class_id: int) -> Dict[str, Any]:
        """
        CSVファイルからインポート
        
        Args:
            file_data: CSVファイルデータ
            class_id: クラスID
            
        Returns:
            Dict: インポート結果
        """
        try:
            # CSVデータの読み込み
            csv_content = file_data.read().decode('utf-8')
            csv_reader = csv.reader(io.StringIO(csv_content))
            
            curriculum_data = {}
            units_data = []
            rubric_data = {'evaluation_aspects': {}, 'rubric': []}
            in_units_section = False
            in_rubric_section = False
            current_rubric_item = None
            
            for row in csv_reader:
                if len(row) < 2:
                    continue
                
                if row[0] == '単元一覧':
                    in_units_section = True
                    in_rubric_section = False
                    continue
                elif row[0] == 'ルーブリック情報':
                    in_rubric_section = True
                    in_units_section = False
                    continue
                elif row[0] == 'ルーブリック詳細':
                    in_rubric_section = True
                    continue
                elif row[0] == '項目名' and in_rubric_section:
                    continue  # ルーブリックヘッダー行をスキップ
                elif row[0] == '順序' and in_units_section:
                    continue  # 単元ヘッダー行をスキップ
                elif in_units_section and row[0] != '':
                    # 単元データ
                    if len(row) >= 4:
                        units_data.append({
                            'order_index': int(row[0]) if row[0].isdigit() else 1,
                            'title': row[1],
                            'description': row[2],
                            'duration_weeks': int(row[3]) if row[3].isdigit() else 1
                        })
                elif in_rubric_section and len(row) >= 5:
                    # ルーブリック詳細データ
                    rubric_data['rubric'].append({
                        'category': row[0],
                        'description': row[1],
                        'levels': [row[2], row[3], row[4]]
                    })
                elif not in_units_section and not in_rubric_section:
                    # 基本情報
                    key, value = row[0], row[1]
                    if key == 'タイトル':
                        curriculum_data['title'] = value
                    elif key == '説明':
                        curriculum_data['description'] = value
                    elif key == '総授業数':
                        curriculum_data['total_classes'] = int(value) if value.isdigit() else 35
                    elif key == '総時間数':
                        curriculum_data['total_hours'] = float(value) if value.replace('.', '').isdigit() else 29.2
                    elif key == '難易度':
                        curriculum_data['difficulty_level'] = int(value) if value.isdigit() else 2
                    elif key == '自己ペースモード':
                        curriculum_data['self_paced_mode'] = value if value else 'flexible'
                    elif key == 'コンテンツ':
                        curriculum_data['content'] = value
                    elif key == '評価観点_知識技能':
                        rubric_data['evaluation_aspects']['knowledge'] = int(value) if value.isdigit() else 30
                    elif key == '評価観点_思考判断表現':
                        rubric_data['evaluation_aspects']['thinking'] = int(value) if value.isdigit() else 40
                    elif key == '評価観点_主体的態度':
                        rubric_data['evaluation_aspects']['attitude'] = int(value) if value.isdigit() else 30
            
            # curriculum_dataにルーブリック情報を統合
            if rubric_data['evaluation_aspects'] or rubric_data['rubric']:
                curriculum_data['curriculum_data'] = json.dumps({
                    'evaluation_aspects': rubric_data['evaluation_aspects'],
                    'rubric': rubric_data['rubric']
                }, ensure_ascii=False)
            
            return {
                "success": True,
                "curriculum_data": curriculum_data,
                "units_data": units_data,
                "rubric_data": rubric_data,
                "message": f"CSVから{len(units_data)}個の単元を含むカリキュラムデータを読み込みました"
            }

        except Exception as e:
            logger.error(f"Error importing from CSV: {str(e)}")
            return {
                "success": False,
                "message": f"CSV読み込み中にエラーが発生しました: {str(e)}"
            }

    def _import_from_json(self, file_data: Any, class_id: int) -> Dict[str, Any]:
        """
        JSONファイルからインポート
        
        Args:
            file_data: JSONファイルデータ
            class_id: クラスID
            
        Returns:
            Dict: インポート結果
        """
        try:
            # JSONデータの読み込み
            json_content = file_data.read().decode('utf-8')
            imported_data = json.loads(json_content)
            
            # データ構造の検証
            if not isinstance(imported_data, dict):
                return {
                    "success": False,
                    "message": "無効なJSON形式です"
                }
            
            # カリキュラムデータの抽出
            curriculum_data = {
                'title': imported_data.get('title', ''),
                'description': imported_data.get('description', ''),
                'total_classes': imported_data.get('total_classes', 35),
                'total_hours': imported_data.get('total_hours', 29.2),
                'difficulty_level': imported_data.get('difficulty_level', 2),
                'self_paced_mode': imported_data.get('self_paced_mode', 'flexible'),
                'content': json.dumps(imported_data.get('content', {}), ensure_ascii=False)
            }
            
            # 単元データの抽出
            units_data = imported_data.get('units', [])
            
            return {
                "success": True,
                "curriculum_data": curriculum_data,
                "units_data": units_data,
                "message": f"JSONから{len(units_data)}個の単元を含むカリキュラムデータを読み込みました"
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return {
                "success": False,
                "message": "無効なJSON形式です"
            }
        except Exception as e:
            logger.error(f"Error importing from JSON: {str(e)}")
            return {
                "success": False,
                "message": f"JSON読み込み中にエラーが発生しました: {str(e)}"
            }

    def create_curriculum_template(self) -> Dict[str, Any]:
        """
        カリキュラムテンプレートを作成
        
        Returns:
            Dict: テンプレート結果
        """
        try:
            # CSVテンプレートの作成
            csv_template = self._create_csv_template()
            
            # JSONテンプレートの作成
            json_template = self._create_json_template()
            
            return {
                "success": True,
                "csv_template": csv_template,
                "json_template": json_template
            }

        except Exception as e:
            logger.error(f"Error creating curriculum template: {str(e)}")
            return {
                "success": False,
                "message": f"テンプレート作成中にエラーが発生しました: {str(e)}"
            }

    def _create_csv_template(self) -> str:
        """
        CSVテンプレートを作成
        
        Returns:
            str: CSVテンプレート文字列
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 基本情報テンプレート
        writer.writerow(['項目', '内容'])
        writer.writerow(['タイトル', 'サンプルカリキュラム'])
        writer.writerow(['説明', 'これはサンプルのカリキュラムです'])
        writer.writerow(['総授業数', '35'])
        writer.writerow(['総時間数', '29.2'])
        writer.writerow(['難易度', '2'])
        writer.writerow(['自己ペースモード', 'flexible'])
        
        # 単元テンプレート
        writer.writerow(['', ''])
        writer.writerow(['単元一覧', ''])
        writer.writerow(['順序', 'タイトル', '説明', '期間（週）'])
        writer.writerow(['1', '基礎理解', '基本概念を学習します', '4'])
        writer.writerow(['2', '応用学習', '応用問題を解決します', '6'])
        writer.writerow(['3', '発展探究', '発展的な内容を探究します', '4'])
        
        # ルーブリックテンプレート
        writer.writerow(['', ''])
        writer.writerow(['ルーブリック情報', ''])
        writer.writerow(['評価観点_知識技能', '30'])
        writer.writerow(['評価観点_思考判断表現', '40'])
        writer.writerow(['評価観点_主体的態度', '30'])
        writer.writerow(['', ''])
        writer.writerow(['ルーブリック詳細', ''])
        writer.writerow(['項目名', '説明', '優秀(A)', '良好(B)', '要改善(C)'])
        writer.writerow(['知識の理解', '基本的な知識や概念の理解度', '重要な概念を正確に理解し、他の概念との関連も説明できる', '基本的な概念を理解し、簡単な例で説明できる', '概念の理解が不十分で、説明に誤りがある'])
        writer.writerow(['問題解決力', '問題を分析し適切な解決策を見つける能力', '複雑な問題を体系的に分析し、創造的な解決策を提案できる', '基本的な問題に対して適切な解決策を見つけることができる', '問題の分析が表面的で、解決策が不適切である'])
        
        # コンテンツテンプレート
        writer.writerow(['', ''])
        writer.writerow(['コンテンツ', '{"phases": [{"name": "基礎", "description": "基本学習"}]}'])
        
        return output.getvalue()

    def _create_json_template(self) -> Dict[str, Any]:
        """
        JSONテンプレートを作成
        
        Returns:
            Dict: JSONテンプレート
        """
        return {
            "title": "サンプルカリキュラム",
            "description": "これはサンプルのカリキュラムです",
            "total_classes": 35,
            "total_hours": 29.2,
            "difficulty_level": 2,
            "self_paced_mode": "flexible",
            "units": [
                {
                    "order_index": 1,
                    "title": "基礎理解",
                    "description": "基本概念を学習します",
                    "duration_weeks": 4
                },
                {
                    "order_index": 2,
                    "title": "応用学習", 
                    "description": "応用問題を解決します",
                    "duration_weeks": 6
                },
                {
                    "order_index": 3,
                    "title": "発展探究",
                    "description": "発展的な内容を探究します", 
                    "duration_weeks": 4
                }
            ],
            "content": {
                "phases": [
                    {"name": "基礎", "description": "基本学習"},
                    {"name": "応用", "description": "応用学習"},
                    {"name": "発展", "description": "発展学習"}
                ]
            }
        }