#!/usr/bin/env python3
"""
Database Column Usage Audit
Analyzes which database columns are actually used in the codebase
"""

import os
import re
import sys
from pathlib import Path

def analyze_database_columns():
    """Analyze database column usage"""
    project_path = Path('/home/masat/claude-projects/QuestEd')
    
    # Common database column patterns that might be unused
    potentially_unused_columns = [
        'created_by',
        'updated_by', 
        'deleted_at',
        'is_deleted',
        'version',
        'metadata',
        'legacy_id',
        'old_id',
        'temp_field',
        'backup_data',
        'migration_flag',
        'test_field'
    ]
    
    # Known tables from the database
    known_tables = [
        'users', 'schools', 'classes', 'curriculum_units', 'proficiency_records',
        'answer_records', 'text_deliveries', 'problem_categories', 'rankings',
        'chat_history', 'activity_logs', 'goals', 'todos', 'inquiry_themes'
    ]
    
    # Find all Python files
    py_files = []
    for pattern in ['app/**/*.py', 'basebuilder/**/*.py', '*.py']:
        py_files.extend(project_path.glob(pattern))
    
    # Track column references
    column_references = {}
    
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding='utf-8')
            
            # Look for database column references
            # Pattern: model.column_name or db.Column references
            column_patterns = [
                r'\.(\w+)\s*==',  # model.column_name ==
                r'\.(\w+)\s*!=',  # model.column_name !=
                r'\.(\w+)\s*>',   # model.column_name >
                r'\.(\w+)\s*<',   # model.column_name <
                r'\.(\w+)\s*\)',  # model.column_name)
                r'\.(\w+)\s*,',   # model.column_name,
                r'order_by\([^)]*\.(\w+)',  # order_by(model.column)
                r'filter\([^)]*\.(\w+)',    # filter(model.column)
                r'db\.Column\([^)]*comment=[\'"]([^\'\"]*)[\'"]',  # column comments
            ]
            
            for pattern in column_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match not in column_references:
                        column_references[match] = []
                    column_references[match].append(str(py_file))
                    
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    # Analyze models for unused columns
    models_dir = project_path / 'app' / 'models'
    basebuilder_models = project_path / 'basebuilder' / 'models.py'
    
    model_columns = {}
    
    # Parse model files for column definitions
    for model_file in [models_dir / '__init__.py', basebuilder_models]:
        if model_file.exists():
            try:
                content = model_file.read_text(encoding='utf-8')
                
                # Find model class definitions
                model_matches = re.findall(r'class\s+(\w+)\s*\([^)]*db\.Model[^)]*\):', content)
                
                for model_name in model_matches:
                    model_columns[model_name] = []
                    
                    # Find the model class block
                    class_pattern = rf'class\s+{model_name}\s*\([^)]*db\.Model[^)]*\):(.*?)(?=class\s+\w+|$)'
                    class_match = re.search(class_pattern, content, re.DOTALL)
                    
                    if class_match:
                        class_content = class_match.group(1)
                        
                        # Find column definitions
                        column_matches = re.findall(r'(\w+)\s*=\s*db\.Column', class_content)
                        model_columns[model_name].extend(column_matches)
                        
            except Exception as e:
                print(f"Error parsing {model_file}: {e}")
    
    return {
        'column_references': column_references,
        'model_columns': model_columns,
        'potentially_unused': potentially_unused_columns
    }

def main():
    print("Analyzing database column usage...")
    results = analyze_database_columns()
    
    print("\n" + "="*60)
    print("DATABASE COLUMN USAGE ANALYSIS")
    print("="*60)
    
    print(f"\nMODELS AND THEIR COLUMNS:")
    for model, columns in results['model_columns'].items():
        print(f"\n{model}:")
        for col in columns:
            print(f"  - {col}")
    
    print(f"\nCOLUMN REFERENCES FOUND ({len(results['column_references'])}):")
    for col, files in sorted(results['column_references'].items()):
        print(f"  {col}: {len(files)} references")
    
    print(f"\nPOTENTIALLY UNUSED COLUMNS:")
    for col in results['potentially_unused']:
        if col in results['column_references']:
            print(f"  {col}: USED ({len(results['column_references'][col])} refs)")
        else:
            print(f"  {col}: POTENTIALLY UNUSED")

if __name__ == '__main__':
    main()