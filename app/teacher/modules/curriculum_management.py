# app/teacher/modules/curriculum_management.py
"""カリキュラム管理機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import json
import csv
import io
import logging

from app.models import (
    db, User, Class, MainTheme, Curriculum, CurriculumUnit,
    ProblemCategory, Subject
)
from app.ai import generate_curriculum_with_ai
from app.services.curriculum_bridge_service import CurriculumBridgeService
from ..common import teacher_required

curriculum_management_bp = Blueprint('teacher_curriculum_management', __name__)

@curriculum_management_bp.route('/class/<int:class_id>/curriculums')
@login_required
@teacher_required
def view_curriculums(class_id):
    """カリキュラム一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを表示する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    curriculums = Curriculum.query.filter_by(
        class_id=class_id,
        teacher_id=current_user.id
    ).all()
    
    # 各カリキュラムの変換状況を取得
    curriculum_stats = []
    for curriculum in curriculums:
        conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
        curriculum_stats.append({
            'curriculum': curriculum,
            'is_converted': conversion_status.get('is_converted', False),
            'converted_units': conversion_status.get('converted_units', 0),
            'conversion_date': conversion_status.get('conversion_date')
        })
    
    return render_template('curriculums.html', 
                         class_obj=class_obj, 
                         curriculums=curriculums,
                         curriculum_stats=curriculum_stats)

@curriculum_management_bp.route('/class/<int:class_id>/curriculum/create')
@login_required
@teacher_required
def create_curriculum_form(class_id):
    """カリキュラム作成フォーム"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    # 教科情報を取得
    subjects = Subject.query.filter_by(is_active=True).all()
    
    return render_template('create_curriculum.html', 
                         class_obj=class_obj,
                         main_themes=main_themes,
                         subjects=subjects)

@curriculum_management_bp.route('/class/<int:class_id>/curriculum/generate', methods=['POST'])
@login_required
@teacher_required
def generate_curriculum(class_id):
    """AIによるカリキュラム生成"""
    try:
        class_obj = Class.query.get_or_404(class_id)
        # 権限チェック
        if class_obj.teacher_id != current_user.id:
            return jsonify({'error': '権限がありません'}), 403
        
        # フォームデータとJSONデータの両方に対応
        if request.is_json:
            data = request.get_json()
        else:
            # 通常のフォームデータの場合
            data = {
                'title': request.form.get('title', ''),
                'subject': request.form.get('subject', ''),
                'grade': request.form.get('grade', ''),
                'duration': request.form.get('duration', ''),
                'focus_areas': request.form.get('focus_areas', ''),
                'difficulty_level': request.form.get('difficulty_level', 'medium'),
                'learning_objectives': request.form.get('learning_objectives', '')
            }
        
        if not data or not data.get('title'):
            return jsonify({'error': 'タイトルは必須です'}), 400
        
        # AIでカリキュラムを生成
        try:
            curriculum_content = generate_curriculum_with_ai(data)
        except Exception as ai_error:
            current_app.logger.error(f"AI generation error: {str(ai_error)}")
            # フォールバック
            curriculum_content = {
                'title': data.get('title'),
                'description': f"{class_obj.name}のカリキュラム",
                'content': '1. 基礎学習\n2. 応用学習\n3. 発展学習',
                'format': 'json'
            }
        
        # カリキュラムを保存
        new_curriculum = Curriculum(
            class_id=class_id,
            title=curriculum_content.get('title', data.get('title')),
            description=curriculum_content.get('description', ''),
            content=curriculum_content.get('content', ''),
            format=curriculum_content.get('format', 'text'),
            teacher_id=current_user.id,
            subject_id=class_obj.subject_id
        )
        db.session.add(new_curriculum)
        db.session.commit()
        
        # フォームからのリクエストの場合はリダイレクト
        if not request.is_json:
            flash('カリキュラムが作成されました。', 'success')
            return redirect(url_for('teacher_curriculum_management.view_curriculums', class_id=class_id))
        
        # JSONリクエストの場合
        return jsonify({
            'success': True,
            'curriculum_id': new_curriculum.id,
            'redirect': url_for('teacher_curriculum_management.view_curriculums', class_id=class_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Curriculum generation error: {str(e)}")
        db.session.rollback()
        
        if not request.is_json:
            flash('カリキュラムの生成に失敗しました。', 'error')
            return redirect(url_for('teacher_curriculum_management.create_curriculum_form', class_id=class_id))
        
        return jsonify({
            'error': 'カリキュラムの生成に失敗しました',
            'details': str(e)
        }), 500

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>')
@login_required
@teacher_required
def view_curriculum(curriculum_id):
    """カリキュラム詳細表示"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを表示する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # 変換状況を取得
    conversion_status = CurriculumBridgeService.get_conversion_status(curriculum_id)
    
    # 関連する単元を取得
    converted_units = []
    if conversion_status.get('is_converted', False):
        converted_units = CurriculumUnit.query.filter_by(
            legacy_curriculum_id=curriculum_id,
            is_active=True
        ).all()
    
    return render_template('view_curriculum.html', 
                         curriculum=curriculum,
                         conversion_status=conversion_status,
                         converted_units=converted_units)

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_curriculum(curriculum_id):
    """カリキュラム編集"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを編集する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        try:
            curriculum.title = request.form.get('title', curriculum.title)
            curriculum.description = request.form.get('description', curriculum.description)
            curriculum.content = request.form.get('content', curriculum.content)
            
            # JSONデータとして保存する場合
            if request.form.get('format') == 'json':
                try:
                    # JSON形式の検証
                    json.loads(curriculum.content)
                    curriculum.format = 'json'
                except json.JSONDecodeError:
                    flash('無効なJSON形式です。', 'error')
                    return render_template('edit_curriculum.html', curriculum=curriculum)
            else:
                curriculum.format = 'text'
            
            curriculum.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('カリキュラムが更新されました。', 'success')
            return redirect(url_for('teacher_curriculum_management.view_curriculum', curriculum_id=curriculum_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Curriculum update error: {str(e)}")
            flash('カリキュラムの更新に失敗しました。', 'error')
    
    return render_template('edit_curriculum.html', curriculum=curriculum)

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/delete')
@login_required
@teacher_required
def delete_curriculum(curriculum_id):
    """カリキュラム削除"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを削除する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    class_id = curriculum.class_id
    
    try:
        # 関連する変換済み単元も削除
        converted_units = CurriculumUnit.query.filter_by(legacy_curriculum_id=curriculum_id).all()
        for unit in converted_units:
            db.session.delete(unit)
        
        db.session.delete(curriculum)
        db.session.commit()
        
        flash('カリキュラムが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Curriculum deletion error: {str(e)}")
        flash('カリキュラムの削除に失敗しました。', 'error')
    
    return redirect(url_for('teacher_curriculum_management.view_curriculums', class_id=class_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/export')
@login_required
@teacher_required
def export_curriculum(curriculum_id):
    """カリキュラムエクスポート"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムをエクスポートする権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    try:
        # エクスポートデータを準備
        export_data = {
            'title': curriculum.title,
            'description': curriculum.description,
            'content': curriculum.content,
            'format': curriculum.format,
            'created_at': curriculum.created_at.isoformat() if curriculum.created_at else None,
            'updated_at': curriculum.updated_at.isoformat() if curriculum.updated_at else None
        }
        
        # JSONファイルとしてダウンロード
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=curriculum_{curriculum_id}.json'}
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Curriculum export error: {str(e)}")
        flash('カリキュラムのエクスポートに失敗しました。', 'error')
        return redirect(url_for('teacher_curriculum_management.view_curriculum', curriculum_id=curriculum_id))

@curriculum_management_bp.route('/class/<int:class_id>/curriculum/import', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_curriculum(class_id):
    """カリキュラムインポート"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにカリキュラムをインポートする権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません。')
            return render_template('import_curriculum.html', class_obj=class_obj)
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません。')
            return render_template('import_curriculum.html', class_obj=class_obj)
        
        try:
            # JSONファイルを読み込み
            file_content = file.read().decode('utf-8')
            curriculum_data = json.loads(file_content)
            
            # 必須フィールドの確認
            required_fields = ['title', 'content']
            for field in required_fields:
                if field not in curriculum_data:
                    flash(f'必須フィールド "{field}" がありません。', 'error')
                    return render_template('import_curriculum.html', class_obj=class_obj)
            
            # カリキュラムを作成
            new_curriculum = Curriculum(
                class_id=class_id,
                title=curriculum_data['title'],
                description=curriculum_data.get('description', ''),
                content=curriculum_data['content'],
                format=curriculum_data.get('format', 'text'),
                teacher_id=current_user.id,
                subject_id=class_obj.subject_id
            )
            
            db.session.add(new_curriculum)
            db.session.commit()
            
            flash('カリキュラムがインポートされました。', 'success')
            return redirect(url_for('teacher_curriculum_management.view_curriculums', class_id=class_id))
            
        except json.JSONDecodeError:
            flash('無効なJSONファイルです。', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Curriculum import error: {str(e)}")
            flash('カリキュラムのインポートに失敗しました。', 'error')
    
    return render_template('import_curriculum.html', class_obj=class_obj)

@curriculum_management_bp.route('/download_curriculum_template')
@login_required
@teacher_required
def download_curriculum_template():
    """カリキュラムテンプレートダウンロード"""
    template_data = {
        'title': 'サンプルカリキュラム',
        'description': 'カリキュラムの説明',
        'content': '1. 導入\n2. 展開\n3. まとめ',
        'format': 'text'
    }
    
    response = Response(
        json.dumps(template_data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=curriculum_template.json'}
    )
    
    return response

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/convert')
@login_required
@teacher_required
def convert_curriculum_to_units(curriculum_id):
    """カリキュラムを単元に変換"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを変換する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    try:
        # CurriculumBridgeServiceを使用して変換
        result = CurriculumBridgeService.convert_curriculum_to_units(
            curriculum_id=curriculum_id,
            created_by=current_user.id
        )
        
        if result['success']:
            flash(f'カリキュラムが{result["units_created"]}個の単元に変換されました。', 'success')
        else:
            flash(f'変換に失敗しました: {result["error"]}', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Curriculum conversion error: {str(e)}")
        flash('カリキュラムの変換中にエラーが発生しました。', 'error')
    
    return redirect(url_for('teacher_curriculum_management.view_curriculum', curriculum_id=curriculum_id))

@curriculum_management_bp.route('/curriculum/<int:curriculum_id>/units')
@login_required
@teacher_required
def view_converted_units(curriculum_id):
    """変換済み単元一覧"""
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('この情報を表示する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    # 変換済み単元を取得
    converted_units = CurriculumUnit.query.filter_by(
        legacy_curriculum_id=curriculum_id,
        is_active=True
    ).order_by(CurriculumUnit.order_index).all()
    
    return render_template('converted_units.html', 
                         curriculum=curriculum,
                         converted_units=converted_units)

@curriculum_management_bp.route('/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_unit(unit_id):
    """単元編集"""
    unit = CurriculumUnit.query.get_or_404(unit_id)
    
    # 権限チェック
    if unit.created_by != current_user.id:
        flash('この単元を編集する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    if request.method == 'POST':
        try:
            unit.title = request.form.get('title', unit.title)
            unit.description = request.form.get('description', unit.description)
            unit.learning_objectives = request.form.get('learning_objectives', unit.learning_objectives)
            unit.difficulty_level = int(request.form.get('difficulty_level', unit.difficulty_level))
            unit.estimated_minutes = int(request.form.get('estimated_minutes', unit.estimated_minutes or 0))
            
            # タグの処理（JSON形式）
            tags_input = request.form.get('tags', '')
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                unit.tags = json.dumps(tags)
            else:
                unit.tags = None
            
            unit.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('単元が更新されました。', 'success')
            return redirect(url_for('teacher_curriculum_management.view_converted_units', 
                                  curriculum_id=unit.legacy_curriculum_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unit update error: {str(e)}")
            flash('単元の更新に失敗しました。', 'error')
    
    return render_template('edit_unit.html', unit=unit)

@curriculum_management_bp.route('/unit/<int:unit_id>/delete')
@login_required
@teacher_required
def delete_unit(unit_id):
    """単元削除"""
    unit = CurriculumUnit.query.get_or_404(unit_id)
    
    # 権限チェック
    if unit.created_by != current_user.id:
        flash('この単元を削除する権限がありません。')
        return redirect(url_for('teacher_class_management.classes'))
    
    curriculum_id = unit.legacy_curriculum_id
    
    try:
        # 単元を非アクティブに設定（完全削除ではなく）
        unit.is_active = False
        unit.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('単元が削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unit deletion error: {str(e)}")
        flash('単元の削除に失敗しました。', 'error')
    
    return redirect(url_for('teacher_curriculum_management.view_converted_units', curriculum_id=curriculum_id))