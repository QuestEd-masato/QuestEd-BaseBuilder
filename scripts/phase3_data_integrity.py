#!/usr/bin/env python3
"""
Phase 3: データ整合性確保スクリプト
=====================================================================
CLAUDE.mdの仕様に基づき、データベースの整合性を確保するための
マイグレーションスクリプトを生成します。

実行方法:
1. python scripts/phase3_data_integrity.py --generate-sql > migration.sql
2. SQLファイルを確認後、DBに適用
3. python scripts/phase3_data_integrity.py --create-mappings

注意: インデントエラーや重複定義がないよう慎重に実装
"""

import argparse
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import (
    db, CurriculumUnit, Curriculum, BasicKnowledgeItem,
    StudentUnitSelection, Class, AnswerRecord
)


class DataIntegrityManager:
    """データ整合性管理クラス"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
    
    def generate_sql_fixes(self) -> List[str]:
        """データ修正用SQLを生成"""
        sql_statements = []
        
        # 1. curriculum_units の created_by 修正
        sql_statements.append("""
-- Phase 3.1: curriculum_units の created_by 修正
-- カリキュラムの教師IDを単元に反映
UPDATE curriculum_units cu
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
SET cu.created_by = c.teacher_id
WHERE cu.created_by IS NULL OR cu.created_by != c.teacher_id;
""")
        
        # 2. school_id 設定
        sql_statements.append("""
-- Phase 3.1: curriculum_units の school_id 設定
-- クラスの学校IDを単元に反映
UPDATE curriculum_units cu  
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
JOIN classes cl ON c.class_id = cl.id
SET cu.school_id = cl.school_id
WHERE cu.school_id IS NULL;
""")
        
        # 3. subject_id の整合性確保
        sql_statements.append("""
-- Phase 3.1: curriculum_units の subject_id 設定
-- カリキュラムの教科IDを単元に反映
UPDATE curriculum_units cu
JOIN curriculums c ON cu.legacy_curriculum_id = c.id
SET cu.subject_id = c.subject_id
WHERE cu.subject_id IS NULL AND c.subject_id IS NOT NULL;
""")
        
        # 4. 完了済み単元の approval_status 移行
        sql_statements.append("""
-- Phase 3.1: 完了済み単元の承認ステータス移行
-- 進捗80%以上の単元を approved に設定
UPDATE student_unit_selections
SET approval_status = 'approved',
    approved_at = NOW(),
    teacher_comments = '既存学習データからの自動承認'
WHERE progress_percentage >= 80.0 
    AND approval_status = 'none'
    AND status = 'completed';
""")
        
        # 5. 学習時間の整合性確保
        sql_statements.append("""
-- Phase 3.1: 学習時間の整合性確保
-- NULL値を0に設定
UPDATE student_unit_selections
SET study_time_minutes = 0
WHERE study_time_minutes IS NULL;
""")
        
        # 6. ステータスの整合性確保
        sql_statements.append("""
-- Phase 3.1: ステータスの整合性確保
-- 進捗に基づいてステータスを更新
UPDATE student_unit_selections
SET status = CASE
    WHEN progress_percentage = 0 THEN 'not_started'
    WHEN progress_percentage >= 100 THEN 'completed'
    ELSE 'in_progress'
END
WHERE status IS NULL OR status = '';
""")
        
        return sql_statements
    
    def create_unit_item_mappings(self) -> Dict[str, any]:
        """単元と問題の自動マッピング作成"""
        
        # 現在のカリキュラム単元を取得
        units = CurriculumUnit.query.filter_by(is_active=True).all()
        
        mapping_results = {
            'total_units': len(units),
            'mapped_units': 0,
            'total_mappings': 0,
            'mappings': []
        }
        
        for unit in units:
            # 単元に関連する問題を特定
            # 1. 教科で絞り込み
            problems = BasicKnowledgeItem.query.filter_by(
                subject_id=unit.subject_id,
                is_active=True
            )
            
            # 2. 難易度で絞り込み
            if unit.difficulty_level:
                problems = problems.filter_by(difficulty_level=unit.difficulty_level)
            
            # 3. タグやキーワードでマッチング（タグがJSON形式の場合）
            unit_tags = []
            if unit.tags:
                try:
                    unit_tags = json.loads(unit.tags) if isinstance(unit.tags, str) else unit.tags
                except:
                    unit_tags = []
            
            matched_problems = []
            for problem in problems.all():
                # タイトルやコンテンツでのキーワードマッチング
                relevance_score = 0
                
                # タグマッチング
                if hasattr(problem, 'tags') and problem.tags:
                    problem_tags = json.loads(problem.tags) if isinstance(problem.tags, str) else []
                    common_tags = set(unit_tags) & set(problem_tags)
                    relevance_score += len(common_tags) * 10
                
                # タイトルマッチング
                if unit.title and problem.content:
                    unit_keywords = set(unit.title.lower().split())
                    problem_text = problem.content.lower()
                    for keyword in unit_keywords:
                        if keyword in problem_text:
                            relevance_score += 5
                
                if relevance_score > 0:
                    matched_problems.append({
                        'problem_id': problem.id,
                        'relevance_score': relevance_score
                    })
            
            # 上位の関連問題を選択（最大50問）
            matched_problems.sort(key=lambda x: x['relevance_score'], reverse=True)
            selected_problems = matched_problems[:50]
            
            if selected_problems:
                mapping_results['mapped_units'] += 1
                mapping_results['total_mappings'] += len(selected_problems)
                mapping_results['mappings'].append({
                    'unit_id': unit.id,
                    'unit_title': unit.title,
                    'problem_count': len(selected_problems),
                    'problems': selected_problems
                })
        
        return mapping_results
    
    def generate_mapping_sql(self, mappings: Dict[str, any]) -> List[str]:
        """マッピング作成用SQLを生成"""
        sql_statements = []
        
        # unit_item_mappings テーブルが存在しない場合の作成SQL
        sql_statements.append("""
-- Phase 3.2: unit_item_mappings テーブル作成（存在しない場合）
CREATE TABLE IF NOT EXISTS unit_item_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unit_id INT NOT NULL,
    item_id INT NOT NULL,
    item_type VARCHAR(50) DEFAULT 'problem',
    weight DECIMAL(5,2) DEFAULT 1.00,
    order_index INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES curriculum_units(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES basic_knowledge_items(id) ON DELETE CASCADE,
    UNIQUE KEY unique_unit_item (unit_id, item_id, item_type),
    KEY idx_unit_id (unit_id),
    KEY idx_item_id (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""")
        
        # 既存データのクリア
        sql_statements.append("""
-- 既存のマッピングをクリア（必要に応じてコメントアウト）
-- TRUNCATE TABLE unit_item_mappings;
""")
        
        # マッピングデータの挿入
        insert_values = []
        for unit_mapping in mappings['mappings']:
            unit_id = unit_mapping['unit_id']
            for idx, problem in enumerate(unit_mapping['problems']):
                weight = problem['relevance_score'] / 10.0  # 重みを正規化
                insert_values.append(
                    f"({unit_id}, {problem['problem_id']}, 'problem', {weight:.2f}, {idx})"
                )
        
        if insert_values:
            # バッチ挿入（1000件ずつ）
            batch_size = 1000
            for i in range(0, len(insert_values), batch_size):
                batch = insert_values[i:i + batch_size]
                sql_statements.append(f"""
-- マッピングデータ挿入（バッチ {i//batch_size + 1}）
INSERT INTO unit_item_mappings (unit_id, item_id, item_type, weight, order_index)
VALUES {',\n       '.join(batch)}
ON DUPLICATE KEY UPDATE 
    weight = VALUES(weight),
    order_index = VALUES(order_index),
    updated_at = CURRENT_TIMESTAMP;
""")
        
        return sql_statements
    
    def verify_data_integrity(self) -> Dict[str, any]:
        """データ整合性の検証"""
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # 1. curriculum_units の整合性チェック
        units_check = db.session.execute("""
            SELECT 
                COUNT(*) as total_units,
                SUM(CASE WHEN created_by IS NULL THEN 1 ELSE 0 END) as null_created_by,
                SUM(CASE WHEN school_id IS NULL THEN 1 ELSE 0 END) as null_school_id,
                SUM(CASE WHEN subject_id IS NULL THEN 1 ELSE 0 END) as null_subject_id
            FROM curriculum_units
            WHERE is_active = 1
        """).fetchone()
        
        verification_results['checks'].append({
            'name': 'curriculum_units整合性',
            'total': units_check.total_units,
            'issues': {
                'null_created_by': units_check.null_created_by,
                'null_school_id': units_check.null_school_id,
                'null_subject_id': units_check.null_subject_id
            }
        })
        
        # 2. student_unit_selections の整合性チェック
        selections_check = db.session.execute("""
            SELECT 
                COUNT(*) as total_selections,
                SUM(CASE WHEN progress_percentage >= 80 AND approval_status = 'none' THEN 1 ELSE 0 END) as pending_approvals,
                SUM(CASE WHEN study_time_minutes IS NULL THEN 1 ELSE 0 END) as null_study_time,
                SUM(CASE WHEN status IS NULL OR status = '' THEN 1 ELSE 0 END) as invalid_status
            FROM student_unit_selections
        """).fetchone()
        
        verification_results['checks'].append({
            'name': 'student_unit_selections整合性',
            'total': selections_check.total_selections,
            'issues': {
                'pending_approvals': selections_check.pending_approvals,
                'null_study_time': selections_check.null_study_time,
                'invalid_status': selections_check.invalid_status
            }
        })
        
        # 3. 進捗データの整合性チェック
        progress_check = db.session.execute("""
            SELECT 
                COUNT(*) as total_with_progress,
                AVG(progress_percentage) as avg_progress,
                MIN(progress_percentage) as min_progress,
                MAX(progress_percentage) as max_progress
            FROM student_unit_selections
            WHERE status = 'in_progress'
        """).fetchone()
        
        verification_results['checks'].append({
            'name': '進捗データ整合性',
            'stats': {
                'total_in_progress': progress_check.total_with_progress,
                'avg_progress': float(progress_check.avg_progress or 0),
                'min_progress': float(progress_check.min_progress or 0),
                'max_progress': float(progress_check.max_progress or 0)
            }
        })
        
        return verification_results


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Phase 3 データ整合性確保スクリプト')
    parser.add_argument('--generate-sql', action='store_true', 
                        help='データ修正用SQLを生成')
    parser.add_argument('--create-mappings', action='store_true',
                        help='単元と問題のマッピングを作成')
    parser.add_argument('--verify', action='store_true',
                        help='データ整合性を検証')
    parser.add_argument('--output', type=str, default=None,
                        help='出力ファイルパス（指定しない場合は標準出力）')
    
    args = parser.parse_args()
    
    manager = DataIntegrityManager()
    output_lines = []
    
    if args.generate_sql:
        # データ修正SQLの生成
        sql_statements = manager.generate_sql_fixes()
        output_lines.append("-- Phase 3 データ整合性確保SQL")
        output_lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("-- ================================================")
        output_lines.extend(sql_statements)
    
    if args.create_mappings:
        # マッピング作成
        mappings = manager.create_unit_item_mappings()
        mapping_sql = manager.generate_mapping_sql(mappings)
        
        output_lines.append("\n-- 単元・問題マッピング作成SQL")
        output_lines.append(f"-- 対象単元数: {mappings['total_units']}")
        output_lines.append(f"-- マッピング作成単元数: {mappings['mapped_units']}")
        output_lines.append(f"-- 総マッピング数: {mappings['total_mappings']}")
        output_lines.append("-- ================================================")
        output_lines.extend(mapping_sql)
        
        # マッピング詳細をコメントとして追加
        output_lines.append("\n/*")
        output_lines.append("マッピング詳細:")
        for unit_map in mappings['mappings'][:10]:  # 最初の10件を表示
            output_lines.append(f"  単元ID {unit_map['unit_id']}: {unit_map['unit_title']}")
            output_lines.append(f"    → {unit_map['problem_count']}問の問題をマッピング")
        if len(mappings['mappings']) > 10:
            output_lines.append(f"  ... 他 {len(mappings['mappings']) - 10} 単元")
        output_lines.append("*/")
    
    if args.verify:
        # データ整合性の検証
        verification = manager.verify_data_integrity()
        output_lines.append("\n-- データ整合性検証結果")
        output_lines.append(f"-- 検証日時: {verification['timestamp']}")
        output_lines.append("-- ================================================")
        
        for check in verification['checks']:
            output_lines.append(f"\n-- {check['name']}:")
            if 'total' in check:
                output_lines.append(f"--   総数: {check['total']}")
            if 'issues' in check:
                output_lines.append("--   問題:")
                for issue, count in check['issues'].items():
                    if count > 0:
                        output_lines.append(f"--     {issue}: {count}件")
            if 'stats' in check:
                output_lines.append("--   統計:")
                for stat, value in check['stats'].items():
                    output_lines.append(f"--     {stat}: {value}")
    
    # 出力
    output_text = '\n'.join(output_lines)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"出力を {args.output} に保存しました。")
    else:
        print(output_text)


if __name__ == '__main__':
    main()