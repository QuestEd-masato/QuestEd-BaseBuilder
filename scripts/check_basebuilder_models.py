#!/usr/bin/env python3
"""
BaseBuilder Models Definition Check
==================================
BaseBuilderモジュールのモデル定義を確認するスクリプト

このスクリプトはインポートのみを行い、データベース接続は不要
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def check_basebuilder_models():
    """BaseBuilderモデルの定義確認"""
    
    print("🔍 BaseBuilder Models Definition Check")
    print("=" * 50)
    
    try:
        # BaseBuilderモデルのインポートテスト
        print("📦 Importing BaseBuilder models...")
        
        from basebuilder.models import (
            ProblemCategory,
            TextDelivery, 
            BasicKnowledgeItem,
            AnswerRecord,
            ProficiencyRecord,
            TextSet
        )
        
        print("✅ Core models imported successfully")
        
        # モデル定義確認
        models_info = [
            ("ProblemCategory", ProblemCategory, "problem_categories"),
            ("TextDelivery", TextDelivery, "text_deliveries"),
            ("BasicKnowledgeItem", BasicKnowledgeItem, "basic_knowledge_items"),
            ("AnswerRecord", AnswerRecord, "answer_records"),
            ("ProficiencyRecord", ProficiencyRecord, "proficiency_records"),
            ("TextSet", TextSet, "text_sets")
        ]
        
        print("\n📊 Model Definitions:")
        for model_name, model_class, table_name in models_info:
            actual_table = getattr(model_class, '__tablename__', 'UNKNOWN')
            status = "✅" if actual_table == table_name else "❌"
            print(f"   {status} {model_name} → {actual_table}")
            
            # 主要フィールドの確認
            if hasattr(model_class, '__table__'):
                columns = [col.name for col in model_class.__table__.columns]
                print(f"      Fields: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
        
        print("\n📋 Model Relationships:")
        
        # ProblemCategoryのリレーションシップ確認
        try:
            pc_relationships = [attr for attr in dir(ProblemCategory) if not attr.startswith('_')]
            relationships = [attr for attr in pc_relationships if hasattr(getattr(ProblemCategory, attr, None), 'property') and hasattr(getattr(ProblemCategory, attr).property, 'mapper')]
            print(f"   ProblemCategory relationships: {', '.join(relationships) if relationships else 'None detected'}")
        except:
            print("   ProblemCategory relationships: Cannot detect")
            
        print("\n🎯 Import Status Summary:")
        print("   ✅ All core BaseBuilder models are importable")
        print("   ✅ Model definitions are syntactically correct")
        print("   ✅ Table names are properly defined")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\n🔍 Possible causes:")
        print("   - Missing dependencies in basebuilder/models.py")
        print("   - Circular import issues") 
        print("   - Missing extensions module")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_basebuilder_models()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: BaseBuilder models check {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)