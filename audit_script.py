#!/usr/bin/env python3
"""
QuestEd System Audit Script
Identifies unused templates, routes, models, and other components
"""

import os
import re
import json
import glob
from pathlib import Path
from collections import defaultdict

class QuestEdAuditor:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.templates_dir = self.project_path / 'templates'
        self.static_dir = self.project_path / 'static'
        self.app_dir = self.project_path / 'app'
        self.basebuilder_dir = self.project_path / 'basebuilder'
        
        # Results storage
        self.template_usage = {}
        self.route_usage = {}
        self.model_usage = {}
        self.static_usage = {}
        self.unused_items = {
            'templates': [],
            'routes': [],
            'models': [],
            'static': [],
            'database_columns': []
        }
        
    def find_all_templates(self):
        """Find all template files"""
        templates = []
        if self.templates_dir.exists():
            for template_file in self.templates_dir.rglob('*.html'):
                rel_path = template_file.relative_to(self.templates_dir)
                templates.append(str(rel_path))
        return templates
        
    def find_template_references(self):
        """Find all template references in Python files"""
        template_refs = set()
        
        # Search in app/ directory
        for py_file in self.app_dir.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                # Find render_template calls
                render_matches = re.findall(r'render_template\([\'"]([^\'\"]+)[\'"]', content)
                template_refs.update(render_matches)
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
                
        # Search in basebuilder/ directory
        if self.basebuilder_dir.exists():
            for py_file in self.basebuilder_dir.rglob('*.py'):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    render_matches = re.findall(r'render_template\([\'"]([^\'\"]+)[\'"]', content)
                    template_refs.update(render_matches)
                except Exception as e:
                    print(f"Error reading {py_file}: {e}")
                    
        return template_refs
        
    def find_route_functions(self):
        """Find all route functions"""
        routes = []
        
        # Search in app/ directory
        for py_file in self.app_dir.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                # Find @app.route or @bp.route decorators
                route_matches = re.findall(r'@[\w\.]+\.route\([\'"]([^\'\"]+)[\'"]', content)
                func_matches = re.findall(r'def\s+(\w+)\s*\(', content)
                routes.extend([(py_file, route, func) for route, func in zip(route_matches, func_matches)])
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
                
        # Search in basebuilder/ directory
        if self.basebuilder_dir.exists():
            for py_file in self.basebuilder_dir.rglob('*.py'):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    route_matches = re.findall(r'@[\w\.]+\.route\([\'"]([^\'\"]+)[\'"]', content)
                    func_matches = re.findall(r'def\s+(\w+)\s*\(', content)
                    routes.extend([(py_file, route, func) for route, func in zip(route_matches, func_matches)])
                except Exception as e:
                    print(f"Error reading {py_file}: {e}")
                    
        return routes
        
    def find_model_classes(self):
        """Find all model classes"""
        models = {}
        
        # Search in app/models/
        models_dir = self.app_dir / 'models'
        if models_dir.exists():
            for py_file in models_dir.rglob('*.py'):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    # Find class definitions that inherit from db.Model
                    class_matches = re.findall(r'class\s+(\w+)\s*\([^)]*db\.Model[^)]*\)', content)
                    for class_name in class_matches:
                        models[class_name] = py_file
                except Exception as e:
                    print(f"Error reading {py_file}: {e}")
                    
        # Search in basebuilder/models.py
        basebuilder_models = self.basebuilder_dir / 'models.py'
        if basebuilder_models.exists():
            try:
                content = basebuilder_models.read_text(encoding='utf-8')
                class_matches = re.findall(r'class\s+(\w+)\s*\([^)]*db\.Model[^)]*\)', content)
                for class_name in class_matches:
                    models[class_name] = basebuilder_models
            except Exception as e:
                print(f"Error reading {basebuilder_models}: {e}")
                
        return models
        
    def find_static_files(self):
        """Find all static files"""
        static_files = []
        if self.static_dir.exists():
            for static_file in self.static_dir.rglob('*'):
                if static_file.is_file():
                    rel_path = static_file.relative_to(self.static_dir)
                    static_files.append(str(rel_path))
        return static_files
        
    def find_static_references(self):
        """Find references to static files in templates and Python code"""
        static_refs = set()
        
        # Search in templates
        if self.templates_dir.exists():
            for template_file in self.templates_dir.rglob('*.html'):
                try:
                    content = template_file.read_text(encoding='utf-8')
                    # Find url_for('static', filename='...') calls
                    static_matches = re.findall(r'url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'\"]+)[\'"]', content)
                    static_refs.update(static_matches)
                    
                    # Find direct references to static files
                    static_matches = re.findall(r'/static/([^\'\"\\s]+)', content)
                    static_refs.update(static_matches)
                except Exception as e:
                    print(f"Error reading {template_file}: {e}")
                    
        return static_refs
        
    def analyze_database_columns(self):
        """Analyze database model columns for unused ones"""
        unused_columns = []
        
        # This is a simplified analysis - in practice you'd need to check usage
        # across all Python files to see if columns are referenced
        print("Database column analysis requires deeper code analysis...")
        
        return unused_columns
        
    def run_audit(self):
        """Run the complete audit"""
        print("Starting QuestEd System Audit...")
        
        # Find all templates
        all_templates = self.find_all_templates()
        print(f"Found {len(all_templates)} template files")
        
        # Find template references
        template_refs = self.find_template_references()
        print(f"Found {len(template_refs)} template references")
        
        # Find unused templates
        unused_templates = []
        for template in all_templates:
            if template not in template_refs:
                unused_templates.append(template)
        
        # Find routes
        all_routes = self.find_route_functions()
        print(f"Found {len(all_routes)} route functions")
        
        # Find models
        all_models = self.find_model_classes()
        print(f"Found {len(all_models)} model classes")
        
        # Find static files
        all_static = self.find_static_files()
        static_refs = self.find_static_references()
        unused_static = []
        for static_file in all_static:
            if static_file not in static_refs:
                unused_static.append(static_file)
        
        # Generate report
        return {
            'summary': {
                'total_templates': len(all_templates),
                'referenced_templates': len(template_refs),
                'unused_templates': len(unused_templates),
                'total_routes': len(all_routes),
                'total_models': len(all_models),
                'total_static_files': len(all_static),
                'unused_static_files': len(unused_static)
            },
            'unused_templates': unused_templates,
            'unused_static_files': unused_static,
            'all_templates': all_templates,
            'template_references': sorted(list(template_refs)),
            'routes': all_routes,
            'models': all_models,
            'duplicate_analysis': self.find_duplicate_templates()
        }
        
    def find_duplicate_templates(self):
        """Find potentially duplicate templates"""
        duplicates = []
        
        all_templates = self.find_all_templates()
        
        # Group by similar names
        name_groups = defaultdict(list)
        for template in all_templates:
            base_name = os.path.basename(template).replace('.html', '')
            name_groups[base_name].append(template)
            
        # Find groups with multiple templates
        for base_name, templates in name_groups.items():
            if len(templates) > 1:
                duplicates.append({
                    'base_name': base_name,
                    'templates': templates
                })
                
        return duplicates

def main():
    project_path = '/home/masat/claude-projects/QuestEd'
    auditor = QuestEdAuditor(project_path)
    
    try:
        report = auditor.run_audit()
        
        print("\n" + "="*80)
        print("QUESTED SYSTEM AUDIT REPORT")
        print("="*80)
        
        print(f"\nSUMMARY:")
        print(f"- Total templates: {report['summary']['total_templates']}")
        print(f"- Referenced templates: {report['summary']['referenced_templates']}")
        print(f"- Unused templates: {report['summary']['unused_templates']}")
        print(f"- Total routes: {report['summary']['total_routes']}")
        print(f"- Total models: {report['summary']['total_models']}")
        print(f"- Total static files: {report['summary']['total_static_files']}")
        print(f"- Unused static files: {report['summary']['unused_static_files']}")
        
        print(f"\nUNUSED TEMPLATES ({len(report['unused_templates'])}):")
        for template in sorted(report['unused_templates']):
            print(f"  - {template}")
            
        print(f"\nUNUSED STATIC FILES ({len(report['unused_static_files'])}):")
        for static_file in sorted(report['unused_static_files'][:20]):  # Show first 20
            print(f"  - {static_file}")
        if len(report['unused_static_files']) > 20:
            print(f"  ... and {len(report['unused_static_files']) - 20} more")
            
        print(f"\nDUPLICATE TEMPLATE ANALYSIS:")
        for duplicate in report['duplicate_analysis']:
            print(f"  - {duplicate['base_name']}:")
            for template in duplicate['templates']:
                print(f"    - {template}")
                
        print(f"\nREFERENCED TEMPLATES ({len(report['template_references'])}):")
        for ref in report['template_references']:
            print(f"  - {ref}")
            
        # Save detailed report
        with open('/home/masat/claude-projects/QuestEd/audit_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        print(f"\nDetailed report saved to: audit_report.json")
        
    except Exception as e:
        print(f"Error during audit: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()