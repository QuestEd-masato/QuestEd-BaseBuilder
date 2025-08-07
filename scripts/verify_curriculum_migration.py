#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Curriculum Migration Verification Script
=====================================
カリキュラムデータ移行の検証スクリプト

使用方法:
    python scripts/verify_curriculum_migration.py
"""

import os
import sys
import json
import logging

# プロジェクトルートをPATHに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app.models import db, Curriculum
from app.modules.lesson_system.models.lesson_models import CurriculumLesson
from app.services.curriculum.migration_adapter import CurriculumMigrationAdapter

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """アプリケーション作成"""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    
    return app


def verify_curriculum_data_consistency():
    """カリキュラムデータの整合性を検証"""
    results = {
        'total_curriculums': 0,
        'consistent': 0,
        'inconsistent': 0,
        'json_only': 0,
        'table_only': 0,
        'details': []
    }
    
    curriculums = Curriculum.query.all()
    results['total_curriculums'] = len(curriculums)
    
    logger.info(f"Verifying {len(curriculums)} curriculums...")
    
    for curriculum in curriculums:
        logger.info(f"Checking curriculum {curriculum.id}: {curriculum.title}")
        
        # JSON data check
        json_lessons = 0
        if curriculum.curriculum_data:
            try:
                data = json.loads(curriculum.curriculum_data)
                json_lessons = len(data.get('table_content', []))
            except json.JSONDecodeError:
                pass
        
        # Table data check
        table_lessons = CurriculumLesson.query.filter_by(curriculum_id=curriculum.id).count()
        
        # Migration adapter check
        adapter_result = CurriculumMigrationAdapter.verify_data_consistency(curriculum.id)
        
        detail = {
            'curriculum_id': curriculum.id,
            'title': curriculum.title,
            'json_lessons': json_lessons,
            'table_lessons': table_lessons,
            'consistent': adapter_result.get('consistent', False),
            'adapter_message': adapter_result.get('message', '')
        }
        
        if json_lessons == table_lessons:
            if json_lessons == 0:
                detail['status'] = 'both_empty'
            else:
                detail['status'] = 'consistent'
                results['consistent'] += 1
        elif json_lessons > 0 and table_lessons == 0:
            detail['status'] = 'json_only'
            results['json_only'] += 1
        elif json_lessons == 0 and table_lessons > 0:
            detail['status'] = 'table_only'
            results['table_only'] += 1
        else:
            detail['status'] = 'inconsistent'
            results['inconsistent'] += 1
        
        results['details'].append(detail)
        
        logger.info(f"  JSON: {json_lessons}, Table: {table_lessons}, Status: {detail['status']}")
    
    return results


def print_verification_report(results):
    """検証結果をレポート出力"""
    print("\n" + "=" * 60)
    print("CURRICULUM MIGRATION VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total Curriculums: {results['total_curriculums']}")
    print(f"Consistent: {results['consistent']}")
    print(f"Inconsistent: {results['inconsistent']}")
    print(f"JSON Only: {results['json_only']}")
    print(f"Table Only: {results['table_only']}")
    print()
    
    if results['inconsistent'] > 0:
        print("⚠️  INCONSISTENT CURRICULUMS:")
        for detail in results['details']:
            if detail['status'] == 'inconsistent':
                print(f"  Curriculum {detail['curriculum_id']}: {detail['title']}")
                print(f"    JSON: {detail['json_lessons']}, Table: {detail['table_lessons']}")
    
    if results['json_only'] > 0:
        print("\n📝 JSON ONLY CURRICULUMS (Need Migration):")
        for detail in results['details']:
            if detail['status'] == 'json_only':
                print(f"  Curriculum {detail['curriculum_id']}: {detail['title']}")
                print(f"    JSON: {detail['json_lessons']}, Table: {detail['table_lessons']}")
    
    if results['table_only'] > 0:
        print("\n📋 TABLE ONLY CURRICULUMS (Migration Complete):")
        for detail in results['details']:
            if detail['status'] == 'table_only':
                print(f"  Curriculum {detail['curriculum_id']}: {detail['title']}")
                print(f"    JSON: {detail['json_lessons']}, Table: {detail['table_lessons']}")
    
    print("\n" + "=" * 60)
    
    # Migration completion percentage
    migrated = results['consistent'] + results['table_only']
    total = results['total_curriculums']
    if total > 0:
        completion = (migrated / total) * 100
        print(f"Migration Completion: {completion:.1f}% ({migrated}/{total})")
    
    print("=" * 60)


def migrate_json_only_curriculums(results):
    """JSON onlyのカリキュラムを移行"""
    json_only = [d for d in results['details'] if d['status'] == 'json_only']
    
    if not json_only:
        print("✅ No JSON-only curriculums found. Migration not needed.")
        return
    
    print(f"\n🔄 Found {len(json_only)} curriculums that need migration:")
    for detail in json_only:
        print(f"  - Curriculum {detail['curriculum_id']}: {detail['title']}")
    
    confirm = input("\nProceed with migration? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return
    
    successful = 0
    failed = 0
    
    for detail in json_only:
        curriculum_id = detail['curriculum_id']
        print(f"\nMigrating curriculum {curriculum_id}...")
        
        try:
            # Read from JSON using adapter
            content = CurriculumMigrationAdapter._read_from_data_column(curriculum_id)
            if content and content.get('table_content'):
                # Write to table using adapter
                if CurriculumMigrationAdapter._write_to_lessons_table(curriculum_id, content):
                    print(f"✅ Successfully migrated curriculum {curriculum_id}")
                    successful += 1
                else:
                    print(f"❌ Failed to write to table for curriculum {curriculum_id}")
                    failed += 1
            else:
                print(f"⚠️  No content found in JSON for curriculum {curriculum_id}")
        except Exception as e:
            print(f"❌ Error migrating curriculum {curriculum_id}: {str(e)}")
            failed += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")


def main():
    """メイン処理"""
    app = create_app()
    
    with app.app_context():
        print("Starting curriculum migration verification...")
        
        # Verify data consistency
        results = verify_curriculum_data_consistency()
        
        # Print report
        print_verification_report(results)
        
        # Offer migration for JSON-only curriculums
        if results['json_only'] > 0:
            migrate_json_only_curriculums(results)
        
        print("\nVerification complete.")


if __name__ == '__main__':
    main()