# app/teacher/modules/curriculum_management.py
"""カリキュラム管理機能 - Phase8F: Orchestration Pattern適用による超軽量化"""

import logging
from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from app.services.curriculum.curriculum_orchestration_service import CurriculumOrchestrationService
from ..common import teacher_required

logger = logging.getLogger(__name__)
curriculum_management_bp = Blueprint("teacher_curriculum_management", __name__)

# Phase8F: Orchestration Service統合初期化
orchestration_service = CurriculumOrchestrationService()

# Phase8F: 統一エラーハンドリング（軽量化）
def handle_orchestration_result(result):
    """Orchestration結果の統一処理"""
    try:
        if result['success']:
            if 'template' in result:
                return render_template(result['template'], **result['data'])
            elif 'redirect' in result:
                if result.get('message'):
                    flash(result['message'], 'success' if result['success'] else 'error')
                redirect_args = result.get('redirect_args', {})
                return redirect(url_for(result['redirect'], **redirect_args))
        else:
            flash(result['message'], 'error')
            redirect_args = result.get('redirect_args', {})
            return redirect(url_for(result['redirect'], **redirect_args))
    except Exception as e:
        logger.error(f"Error in handle_orchestration_result: {str(e)}", exc_info=True)
        # デバッグ情報を含むエラーメッセージ
        if current_app.config.get('DEBUG'):
            flash(f"エラー: {str(e)}", 'error')
        else:
            flash('申し訳ありません。エラーが発生しました。', 'error')
        return redirect(url_for('teacher.dashboard'))

# Phase8F: View関数の軽量化（Orchestration Pattern適用）

@curriculum_management_bp.route('/curriculums/<int:class_id>')
@login_required
@teacher_required
def view_curriculums(class_id):
    """カリキュラム一覧表示（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.get_curriculums_view(class_id))

@curriculum_management_bp.route('/curriculum/create/<int:class_id>')
@login_required
@teacher_required
def create_curriculum_form(class_id):
    """カリキュラム作成フォーム（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.create_curriculum_view(class_id))

@curriculum_management_bp.route('/curriculum/create/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def create_curriculum(class_id):
    """カリキュラム作成処理（Phase8F統合ファサード）"""
    form_data = request.form.to_dict()
    return handle_orchestration_result(orchestration_service.process_curriculum_creation(class_id, form_data))

@curriculum_management_bp.route('/curriculum/generate/<int:class_id>')
@login_required
@teacher_required
def generate_curriculum_form(class_id):
    """AI カリキュラム生成フォーム（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.generate_curriculum_view(class_id))

@curriculum_management_bp.route('/curriculum/generate/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def generate_curriculum(class_id):
    """AI カリキュラム生成処理（Phase8F統合ファサード）"""
    try:
        form_data = request.get_json() if request.is_json else dict(request.form)
        
        # フォームデータの正規化
        if not request.is_json:
            boolean_fields = ['has_fieldwork', 'has_presentation', 'external_collaboration', 
                            'include_detailed_tasks', 'auto_generate_rubrics', 'enable_auto_approval', 'ai_generate_tasks']
            for field in boolean_fields:
                form_data[field] = request.form.get(field) == 'on'
            form_data['default_task_types'] = request.form.getlist('default_task_types')
            form_data['submission_formats'] = request.form.getlist('submission_formats')
        
        result = orchestration_service.process_curriculum_creation(class_id, form_data)
        
        if request.is_json:
            return jsonify({
                'success': result['success'],
                'message': result['message'],
                'curriculum_id': result.get('curriculum_id')
            })
        else:
            return handle_orchestration_result(result)
            
    except Exception as e:
        logger.error(f"AI generation error: {str(e)}")
        error_msg = "カリキュラム生成中にエラーが発生しました"
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('teacher_curriculum_management.create_curriculum_form', class_id=class_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>')
@login_required
@teacher_required
def curriculum_detail(curriculum_id):
    """カリキュラム詳細表示（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.curriculum_detail_view(curriculum_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/edit')
@login_required
@teacher_required
def edit_curriculum(curriculum_id):
    """カリキュラム編集フォーム（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.edit_curriculum_view(curriculum_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/edit', methods=['POST'])
@login_required
@teacher_required
def update_curriculum(curriculum_id):
    """カリキュラム更新処理（Phase8F統合ファサード）"""
    form_data = request.form.to_dict()
    return handle_orchestration_result(orchestration_service.process_curriculum_update(curriculum_id, form_data))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_curriculum(curriculum_id):
    """カリキュラム削除処理（Phase8F統合ファサード）"""
    return handle_orchestration_result(orchestration_service.process_curriculum_deletion(curriculum_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/export')
@login_required
@teacher_required
def export_curriculum(curriculum_id):
    """カリキュラムエクスポート（Phase8F統合ファサード）"""
    try:
        export_result = orchestration_service.import_export_service.export_curriculum(curriculum_id)
        if not export_result['success']:
            flash(export_result['message'], 'error')
            return redirect(url_for('teacher_curriculum_management.curriculum_detail', curriculum_id=curriculum_id))
        
        return Response(
            export_result['content'],
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=curriculum_{curriculum_id}.json'}
        )
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        flash('エクスポートに失敗しました', 'error')
        return redirect(url_for('teacher_curriculum_management.curriculum_detail', curriculum_id=curriculum_id))

@curriculum_management_bp.route('/curriculum/<int:class_id>/import')
@login_required
@teacher_required
def import_curriculum_form(class_id):
    """カリキュラムインポートフォーム（Phase8F統合ファサード）"""
    try:
        return render_template('teacher/curriculum_import.html', class_id=class_id)
    except Exception as e:
        logger.error(f"Import form error: {str(e)}")
        flash('インポートフォームの表示に失敗しました', 'error')
        return redirect(url_for('teacher.dashboard'))

@curriculum_management_bp.route('/curriculum/<int:class_id>/import', methods=['POST'])
@login_required
@teacher_required
def import_curriculum(class_id):
    """カリキュラムインポート処理（Phase8F統合ファサード）"""
    try:
        if 'file' not in request.files:
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('teacher_curriculum_management.import_curriculum_form', class_id=class_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('teacher_curriculum_management.import_curriculum_form', class_id=class_id))
        
        import_result = orchestration_service.import_export_service.import_curriculum(class_id, file)
        if import_result['success']:
            flash(import_result['message'], 'success')
            return redirect(url_for('teacher_curriculum_management.view_curriculums', class_id=class_id))
        else:
            flash(import_result['message'], 'error')
            return redirect(url_for('teacher_curriculum_management.import_curriculum_form', class_id=class_id))
            
    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        flash('インポートに失敗しました', 'error')
        return redirect(url_for('teacher_curriculum_management.import_curriculum_form', class_id=class_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/rubric')
@login_required
@teacher_required
def edit_curriculum_rubric(curriculum_id):
    """カリキュラムルーブリック編集画面"""
    try:
        result = orchestration_service.data_service.get_curriculum_detail(curriculum_id)
        if result['success']:
            return render_template(
                'teacher/curriculum_rubric_edit.html',
                curriculum=result['curriculum'],
                rubric_info=result.get('rubric_info', {})
            )
        else:
            flash(result['message'], 'error')
            return redirect(url_for('teacher.dashboard'))
    except Exception as e:
        logger.error(f"Rubric edit error: {str(e)}")
        flash('ルーブリック編集画面の表示に失敗しました', 'error')
        return redirect(url_for('teacher.dashboard'))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/rubric', methods=['POST'])
@login_required
@teacher_required
def update_curriculum_rubric(curriculum_id):
    """カリキュラムルーブリック更新処理"""
    try:
        rubric_data = request.json
        update_result = orchestration_service.data_service.update_curriculum(
            curriculum_id,
            {
                'rubric_data': rubric_data.get('rubric', {}),
                'evaluation_aspects': rubric_data.get('evaluation_aspects', {})
            }
        )
        
        if update_result['success']:
            return jsonify({'success': True, 'message': 'ルーブリックを更新しました'})
        else:
            return jsonify({'success': False, 'message': update_result['message']}), 400
            
    except Exception as e:
        logger.error(f"Rubric update error: {str(e)}")
        return jsonify({'success': False, 'message': 'ルーブリックの更新に失敗しました'}), 500

@curriculum_management_bp.route('/curriculum/template/download')
@login_required
@teacher_required
def download_template():
    """テンプレートダウンロード（Phase8F統合ファサード）"""
    try:
        template_result = orchestration_service.import_export_service.generate_template()
        if not template_result['success']:
            flash(template_result['message'], 'error')
            return redirect(url_for('teacher.dashboard'))
        
        return Response(
            template_result['content'],
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=curriculum_template.json'}
        )
        
    except Exception as e:
        logger.error(f"Template download error: {str(e)}")
        flash('テンプレートのダウンロードに失敗しました', 'error')
        return redirect(url_for('teacher.dashboard'))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/lessons/edit')
@login_required
@teacher_required
def edit_curriculum_lessons(curriculum_id):
    """カリキュラムレッスン編集 - 新方式にリダイレクト"""
    # 新方式のレッスン管理画面にリダイレクト
    flash("新しいレッスン管理システムを使用してください。", "info")
    return redirect(url_for('lesson_system.lesson_management'))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/lessons/edit', methods=['POST'])
@login_required
@teacher_required
def update_curriculum_lessons(curriculum_id):
    """カリキュラムレッスン更新 - 新方式にリダイレクト"""
    # 新方式のレッスン管理システムを使用するよう案内
    flash("新しいレッスン管理システムでレッスンを編集してください。", "info")
    return redirect(url_for('lesson_system.lesson_management'))

# Phase8F: 使用されていないレガシー関数は削除済み（Phase1-B重複削減）

def view_curriculum(curriculum_id: int) -> dict:
    """カリキュラム表示（レガシー互換性）"""
    return orchestration_service.data_service.get_curriculum_detail(curriculum_id)