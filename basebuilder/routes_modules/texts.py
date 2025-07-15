"""
BaseBuilder Text Management Routes
=================================
テキストアクセス・表示・配信に関するルートハンドラ

不足していたテキスト機能のルートを実装:
- /my_texts (学生向けテキスト一覧)
- /text_sets (教師向けテキスト管理)
- /text/<int:text_id>/view (テキスト詳細表示)
- /text/<int:text_id>/deliver (テキスト配信)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from typing import Dict, List, Any

from extensions import db
from basebuilder.models import (
    TextSet, TextDelivery, ProblemCategory, BasicKnowledgeItem,
    TextProficiencyRecord, AnswerRecord
)
from app.models import User, Class, ClassEnrollment
from basebuilder.utils import require_roles, handle_db_error
# log_activityは内部で定義されているため、basebuilder.utilsからはインポートしない

texts_bp = Blueprint('texts', __name__, url_prefix='/basebuilder')

@texts_bp.route('/api/text-sets')
@login_required
def api_text_sets():
    """シンプルなBaseBuilder連携用テキスト一覧API"""
    try:
        # 全テキストセットを取得（カテゴリ情報付き）
        text_sets = db.session.query(
            TextSet.id,
            TextSet.title,
            TextSet.description,
            ProblemCategory.name.label('category_name'),
            db.func.count(BasicKnowledgeItem.id).label('problem_count')
        ).outerjoin(
            ProblemCategory, TextSet.category_id == ProblemCategory.id
        ).outerjoin(
            BasicKnowledgeItem, TextSet.id == BasicKnowledgeItem.text_set_id
        ).group_by(
            TextSet.id, TextSet.title, TextSet.description, ProblemCategory.name
        ).order_by(
            ProblemCategory.name, TextSet.title
        ).all()
        
        text_sets_data = []
        for text_set in text_sets:
            text_sets_data.append({
                'id': text_set.id,
                'title': text_set.title,
                'description': text_set.description,
                'category_name': text_set.category_name or 'その他',
                'problem_count': text_set.problem_count or 0
            })
        
        return jsonify({
            'success': True,
            'text_sets': text_sets_data
        })
        
    except Exception as e:
        current_app.logger.error(f"API text-sets error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'テキスト一覧の取得に失敗しました'
        }), 500

@texts_bp.route('/texts')
@login_required
def texts():
    """テキスト管理のメイン画面"""
    if current_user.role == 'student':
        return redirect(url_for('texts.my_texts'))
    else:
        return redirect(url_for('texts.text_sets'))

@texts_bp.route('/dashboard')
@login_required
def dashboard():
    """BaseBuilderダッシュボード"""
    if current_user.role == 'student':
        return redirect(url_for('texts.my_texts'))
    else:
        return redirect(url_for('texts.teacher_dashboard'))

@texts_bp.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    """教師用BaseBuilderダッシュボード"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('教師または管理者のみアクセス可能です。')
            return redirect(url_for('index'))
        
        # 基本統計情報
        total_text_sets = TextSet.query.count()
        total_problems = BasicKnowledgeItem.query.count()
        total_deliveries = TextDelivery.query.count()
        total_categories = ProblemCategory.query.count()
        
        # 教師の場合は自分の学校のデータのみ
        if current_user.role == 'teacher' and hasattr(current_user, 'school_id'):
            teacher_text_sets = TextSet.query.filter(
                db.or_(
                    TextSet.school_id == current_user.school_id,
                    TextSet.school_id == None
                )
            ).count()
            
            teacher_problems = BasicKnowledgeItem.query.filter(
                db.or_(
                    BasicKnowledgeItem.school_id == current_user.school_id,
                    BasicKnowledgeItem.school_id == None
                )
            ).count()
        else:
            teacher_text_sets = total_text_sets
            teacher_problems = total_problems
        
        # 最近の配信記録
        recent_deliveries = TextDelivery.query.order_by(
            TextDelivery.delivered_at.desc()
        ).limit(10).all()
        
        # 最近の問題作成
        recent_problems = BasicKnowledgeItem.query.order_by(
            BasicKnowledgeItem.created_at.desc()
        ).limit(10).all()
        
        # 教師が担当するクラスを取得
        if current_user.role == 'teacher':
            classes = getattr(current_user, 'classes_teaching', [])
        else:
            from app.models import Class
            classes = Class.query.all()
        
        return render_template('basebuilder/teacher_dashboard.html',
                             problem_count=teacher_problems,
                             category_count=total_categories,
                             path_count=0,  # 学習パス数（未実装）
                             classes=classes,
                             recent_problems=recent_problems)
        
    except Exception as e:
        current_app.logger.error(f"Teacher dashboard error: {str(e)}")
        flash('ダッシュボードの読み込み中にエラーが発生しました。')
        return redirect(url_for('index'))

@texts_bp.route('/debug/text_data')
@login_required
def debug_text_data():
    """デバッグ: テキストデータの状況を確認"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # 全テキストセット数
        total_texts = TextSet.query.count()
        
        # 学校別テキスト数
        school_texts = {}
        if hasattr(current_user, 'school_id'):
            school_texts['user_school_id'] = current_user.school_id
            school_texts['user_school_texts'] = TextSet.query.filter_by(
                school_id=current_user.school_id
            ).count()
            school_texts['null_school_texts'] = TextSet.query.filter_by(
                school_id=None
            ).count()
        
        # カテゴリ別テキスト数
        category_texts = db.session.query(
            ProblemCategory.name,
            db.func.count(TextSet.id)
        ).join(
            TextSet, TextSet.category_id == ProblemCategory.id
        ).group_by(ProblemCategory.id).all()
        
        return jsonify({
            'total_texts': total_texts,
            'school_info': school_texts,
            'category_breakdown': [
                {'category': cat, 'count': count} 
                for cat, count in category_texts
            ],
            'user_info': {
                'id': current_user.id,
                'role': current_user.role,
                'school_id': getattr(current_user, 'school_id', None)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_activity(action, description):
    """簡易アクティビティログ記録"""
    try:
        current_app.logger.info(
            f"BASEBUILDER_ACTIVITY: user_id={current_user.id}, "
            f"action={action}, description={description}, "
            f"timestamp={datetime.utcnow()}"
        )
    except Exception as e:
        current_app.logger.error(f"Activity log error: {str(e)}")


@texts_bp.route('/my_texts')
@login_required
def my_texts():
    """学生向け: 配信されたテキスト一覧表示"""
    try:
        # 権限チェック
        if current_user.role != 'student':
            flash('学生のみアクセス可能です。')
            return redirect(url_for('texts.text_sets'))
        # 学生の所属クラスを取得
        enrolled_class_ids = [enrollment.class_id for enrollment in 
                            ClassEnrollment.query.filter_by(
                                student_id=current_user.id,
                                is_active=True
                            ).all()]
        
        if not enrolled_class_ids:
            flash('所属クラスが見つかりません。管理者にお問い合わせください。', 'warning')
            return render_template('basebuilder/my_texts.html', 
                                 deliveries=[], 
                                 text_proficiency={},
                                 now=datetime.now())
        
        # 配信されたテキストを取得
        deliveries = TextDelivery.query.filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).join(TextSet).order_by(
            TextDelivery.delivered_at.desc()
        ).all()
        
        # テキスト習熟度を取得
        text_proficiency = {}
        proficiency_records = TextProficiencyRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        for record in proficiency_records:
            text_proficiency[record.text_set_id] = {
                'level': record.level,
                'last_study': record.updated_at
            }
        
        # アクティビティログ記録
        try:
            from app.models import ActivityLog
            activity = ActivityLog(
                student_id=current_user.id,
                action="text_list_viewed",
                description=f"Student {current_user.id} viewed text list",
                created_at=datetime.now()
            )
            db.session.add(activity)
            db.session.commit()
        except Exception as log_e:
            current_app.logger.warning(f"Activity logging failed: {str(log_e)}")
        
        return render_template('basebuilder/my_texts.html',
                             deliveries=deliveries,
                             text_proficiency=text_proficiency,
                             now=datetime.now())
        
    except Exception as e:
        current_app.logger.error(f"My texts error: {str(e)}")
        flash('テキスト一覧の取得中にエラーが発生しました。', 'error')
        return render_template('basebuilder/my_texts.html', 
                             deliveries=[], 
                             text_proficiency={},
                             now=datetime.now())


@texts_bp.route('/lesson_texts')
@login_required
def lesson_texts():
    """学生向け: レッスンで配信されたBaseBuilderテキスト一覧"""
    try:
        # 権限チェック
        if current_user.role != 'student':
            flash('学生のみアクセス可能です。')
            return redirect(url_for('texts.text_sets'))
        
        # 学生の所属クラスを取得
        from app.models import ClassEnrollment, Curriculum
        from app.modules.lesson_system.models.lesson_models import CurriculumLesson, LessonTask
        enrolled_class_ids = [enrollment.class_id for enrollment in 
                            ClassEnrollment.query.filter_by(
                                student_id=current_user.id,
                                is_active=True
                            ).all()]
        
        if not enrolled_class_ids:
            flash('所属クラスが見つかりません。管理者にお問い合わせください。', 'warning')
            return render_template('basebuilder/lesson_texts.html', 
                                 basebuilder_texts=[],
                                 text_proficiency={},
                                 now=datetime.now())
        
        # クラスに配信されたカリキュラムを取得
        curricula = Curriculum.query.filter(
            Curriculum.class_id.in_(enrolled_class_ids)
        ).all()
        
        # レッスンのタスクから BaseBuilder テキストを抽出
        basebuilder_texts = []
        seen_text_ids = set()  # 重複を避けるため
        
        for curriculum in curricula:
            # カリキュラムのレッスンを取得
            lessons = CurriculumLesson.query.filter_by(
                curriculum_id=curriculum.id
            ).all()
            
            for lesson in lessons:
                # レッスンのタスクを取得
                tasks = LessonTask.query.filter_by(
                    lesson_id=lesson.id
                ).all()
                
                for task in tasks:
                    # タスクの説明からBaseBuilderテキスト情報を抽出
                    if task.description and 'BaseBuilderテキスト:' in task.description:
                        import re
                        pattern = r'BaseBuilderテキスト:\s*"([^"]+)"\s*\(ID:\s*(\d+)\)'
                        match = re.search(pattern, task.description)
                        
                        if match:
                            text_title = match.group(1)
                            text_id = int(match.group(2))
                            
                            if text_id not in seen_text_ids:
                                # TextSetを取得
                                text_set = TextSet.query.get(text_id)
                                if text_set:
                                    seen_text_ids.add(text_id)
                                    basebuilder_texts.append({
                                        'text_set': text_set,
                                        'curriculum_title': curriculum.title,
                                        'lesson_title': lesson.title,
                                        'task_title': task.title,
                                        'lesson_number': lesson.lesson_number
                                    })
        
        # テキスト習熟度を取得
        text_proficiency = {}
        if basebuilder_texts:
            text_ids = [bt['text_set'].id for bt in basebuilder_texts]
            proficiency_records = TextProficiencyRecord.query.filter(
                TextProficiencyRecord.student_id == current_user.id,
                TextProficiencyRecord.text_set_id.in_(text_ids)
            ).all()
            
            for record in proficiency_records:
                text_proficiency[record.text_set_id] = {
                    'level': record.level,
                    'last_study': record.updated_at
                }
        
        # レッスン番号でソート
        basebuilder_texts.sort(key=lambda x: (x['curriculum_title'], x['lesson_number']))
        
        return render_template('basebuilder/lesson_texts.html',
                             basebuilder_texts=basebuilder_texts,
                             text_proficiency=text_proficiency,
                             now=datetime.now())
        
    except Exception as e:
        current_app.logger.error(f"Lesson texts error: {str(e)}")
        flash('テキスト一覧の取得中にエラーが発生しました。', 'error')
        return render_template('basebuilder/lesson_texts.html', 
                             basebuilder_texts=[],
                             text_proficiency={},
                             now=datetime.now())


@texts_bp.route('/text_sets')
@login_required
def text_sets():
    """教師・管理者向け: テキストセット一覧"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('教師または管理者のみアクセス可能です。')
            return redirect(url_for('index'))
        # フィルタリングパラメータ
        category_id = request.args.get('category_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 基本クエリ
        query = TextSet.query
        
        # 教師の場合は自分の学校のテキストのみ
        if current_user.role == 'teacher' and hasattr(current_user, 'school_id'):
            query = query.filter(
                db.or_(
                    TextSet.school_id == current_user.school_id,
                    TextSet.school_id == None  # 全学校共通のテキストも表示
                )
            )
        
        # カテゴリフィルタ
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        # ページネーション
        text_sets_pagination = query.order_by(
            TextSet.created_at.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # カテゴリ一覧
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        
        # デバッグログ
        current_app.logger.info(f"Text sets query for user {current_user.id} (role: {current_user.role}, school_id: {getattr(current_user, 'school_id', 'None')})")
        current_app.logger.info(f"Found {text_sets_pagination.total} text sets")
        
        # 各テキストセットの統計情報を計算
        text_stats = {}
        for text_set in text_sets_pagination.items:
            # 問題数を計算
            problem_count = BasicKnowledgeItem.query.filter_by(
                text_set_id=text_set.id
            ).count()
            
            # 配信データを取得
            deliveries = TextDelivery.query.filter_by(
                text_set_id=text_set.id
            ).all()
            
            text_stats[text_set.id] = {
                'problem_count': problem_count,
                'delivery_count': len(deliveries)
            }
            
            # テキストセットオブジェクトに動的に属性を追加
            # テンプレートで text.problems|length などが使用できるように
            setattr(text_set, '_problem_count', problem_count)
            setattr(text_set, '_delivery_count', len(deliveries))
            setattr(text_set, 'deliveries', deliveries)
        
        return render_template('basebuilder/text_sets.html',
                             text_sets=text_sets_pagination.items,
                             pagination=text_sets_pagination,
                             categories=categories,
                             text_stats=text_stats,
                             selected_category=category_id)
        
    except Exception as e:
        current_app.logger.error(f"Text sets error: {str(e)}")
        flash('テキストセット一覧の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('basebuilder.index'))




@texts_bp.route('/text/<int:text_id>/deliver', methods=['GET', 'POST'])
@login_required
def deliver_text(text_id):
    """教師・管理者向け: テキスト配信"""
    try:
        # 権限チェック
        if current_user.role not in ['admin', 'teacher']:
            flash('教師または管理者のみアクセス可能です。')
            return redirect(url_for('index'))
        
        text_set = TextSet.query.get_or_404(text_id)
        
        # 権限チェック（教師は自分の学校のテキストのみ）
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('このテキストを配信する権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        if request.method == 'POST':
            class_ids = request.form.getlist('class_ids')
            due_date_str = request.form.get('due_date')
            
            if not class_ids:
                flash('配信先クラスを選択してください。', 'error')
                return render_template('basebuilder/deliver_text.html',
                                     text_set=text_set,
                                     classes=_get_available_classes())
            
            # 提出期限の処理
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < date.today():
                        flash('提出期限は今日以降の日付を設定してください。', 'error')
                        return render_template('basebuilder/deliver_text.html',
                                             text_set=text_set,
                                             classes=_get_available_classes())
                except ValueError:
                    flash('無効な日付形式です。', 'error')
                    return render_template('basebuilder/deliver_text.html',
                                         text_set=text_set,
                                         classes=_get_available_classes())
            
            # 配信実行
            success_count = 0
            for class_id in class_ids:
                try:
                    class_id = int(class_id)
                    
                    # 既存の配信をチェック
                    existing_delivery = TextDelivery.query.filter_by(
                        text_set_id=text_id,
                        class_id=class_id
                    ).first()
                    
                    if existing_delivery:
                        continue  # 既に配信済みはスキップ
                    
                    # 新しい配信を作成
                    delivery = TextDelivery(
                        text_set_id=text_id,
                        class_id=class_id,
                        delivered_by=current_user.id,
                        delivered_at=datetime.utcnow(),
                        due_date=due_date
                    )
                    
                    db.session.add(delivery)
                    success_count += 1
                    
                except (ValueError, TypeError):
                    continue
            
            if success_count > 0:
                db.session.commit()
                log_activity("text_delivered", f"Text {text_id} delivered to {success_count} classes")
                flash(f'テキストを{success_count}クラスに配信しました。', 'success')
            else:
                flash('配信できるクラスがありませんでした（既に配信済みの可能性があります）。', 'warning')
            
            return redirect(url_for('texts.text_sets'))
        
        # GET: 配信フォームを表示
        classes = _get_available_classes()
        return render_template('basebuilder/deliver_text.html',
                             text_set=text_set,
                             classes=classes)
        
    except Exception as e:
        current_app.logger.error(f"Deliver text error: {str(e)}")
        flash('テキスト配信中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


def _get_available_classes():
    """利用可能なクラス一覧を取得"""
    if current_user.role == 'admin':
        return Class.query.order_by(Class.name).all()
    elif current_user.role == 'teacher':
        return Class.query.filter_by(
            school_id=current_user.school_id
        ).order_by(Class.name).all()
    else:
        return []


@texts_bp.route('/text/<int:text_id>/problems')
@login_required
@handle_db_error("テキスト問題一覧")
def text_problems(text_id):
    """テキスト内の問題一覧（管理用）"""
    try:
        text_set = TextSet.query.get_or_404(text_id)
        
        # 権限チェック
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('このテキストにアクセスする権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id
        ).order_by(BasicKnowledgeItem.order_in_text).all()
        
        return render_template('basebuilder/text_problems.html',
                             text_set=text_set,
                             problems=problems)
        
    except Exception as e:
        current_app.logger.error(f"Text problems error: {str(e)}")
        flash('問題一覧の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


@texts_bp.route('/import_text_set', methods=['GET', 'POST'])
@login_required
@require_roles(['admin', 'teacher'])
def import_text_set():
    """テキストセットのインポート（CSV）"""
    try:
        if request.method == 'GET':
            # カテゴリ一覧を取得
            categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
            return render_template('basebuilder/import_text.html',
                                 categories=categories)
        
        # POST処理
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        
        if not category_id:
            flash('カテゴリを選択してください。', 'error')
            return redirect(url_for('texts.import_text_set'))
        
        # ファイルチェック
        if 'csv_file' not in request.files:
            flash('CSVファイルを選択してください。', 'error')
            return redirect(url_for('texts.import_text_set'))
        
        csv_file = request.files['csv_file']
        if csv_file.filename == '':
            flash('CSVファイルを選択してください。', 'error')
            return redirect(url_for('texts.import_text_set'))
        
        # CSVファイルの読み込み
        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            flash('CSVファイルのエンコーディングエラー。UTF-8形式で保存してください。', 'error')
            return redirect(url_for('texts.import_text_set'))
        
        # import_text_from_csv関数を使用してインポート
        from basebuilder.importers import import_text_from_csv
        
        success, result, errors = import_text_from_csv(
            csv_content=csv_content,
            title=title,
            description=description,
            category_id=category_id,
            db=db,
            TextSet=TextSet,
            BasicKnowledgeItem=BasicKnowledgeItem,
            current_user_id=current_user.id,
            school_id=getattr(current_user, 'school_id', None)
        )
        
        if success:
            log_activity("text_imported", f"Imported text set: {result.title}")
            flash(f'テキスト「{result.title}」を作成しました。', 'success')
            return redirect(url_for('texts.text_sets'))
        else:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('texts.import_text_set'))
        
    except Exception as e:
        current_app.logger.error(f"Import text set error: {str(e)}")
        flash('テキストのインポート中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


@texts_bp.route('/delete_text_sets', methods=['POST'])
@login_required
@require_roles(['admin', 'teacher'])
def delete_text_sets():
    """テキストセットの一括削除"""
    try:
        text_ids = request.form.getlist('text_ids')
        if not text_ids:
            flash('削除するテキストを選択してください。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        deleted_count = 0
        for text_id in text_ids:
            try:
                text_set = TextSet.query.get(int(text_id))
                if text_set:
                    # 権限チェック
                    if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
                        continue
                    
                    # 関連する配信記録を削除
                    TextDelivery.query.filter_by(text_set_id=text_id).delete()
                    
                    # テキストセットを削除（関連する問題もカスケード削除される想定）
                    db.session.delete(text_set)
                    deleted_count += 1
                    
            except Exception:
                continue
        
        if deleted_count > 0:
            db.session.commit()
            log_activity("texts_deleted", f"Deleted {deleted_count} text sets")
            flash(f'{deleted_count}件のテキストを削除しました。', 'success')
        else:
            flash('削除できるテキストがありませんでした。', 'warning')
        
        return redirect(url_for('texts.text_sets'))
        
    except Exception as e:
        current_app.logger.error(f"Delete text sets error: {str(e)}")
        db.session.rollback()
        flash('テキストの削除中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


@texts_bp.route('/text/<int:text_id>/delete', methods=['POST'])
@login_required
@require_roles(['admin', 'teacher'])
def delete_single_text(text_id):
    """単一テキストセットの削除"""
    try:
        text_set = TextSet.query.get_or_404(text_id)
        
        # 権限チェック
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('このテキストを削除する権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        # 関連する配信記録を削除
        TextDelivery.query.filter_by(text_set_id=text_id).delete()
        
        # テキストセットを削除
        db.session.delete(text_set)
        db.session.commit()
        
        log_activity("text_deleted", f"Deleted text set: {text_set.title}")
        flash(f'テキスト「{text_set.title}」を削除しました。', 'success')
        
        return redirect(url_for('texts.text_sets'))
        
    except Exception as e:
        current_app.logger.error(f"Delete single text error: {str(e)}")
        db.session.rollback()
        flash('テキストの削除中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))


@texts_bp.route('/delivery/<int:delivery_id>/cancel', methods=['POST'])
@login_required
@require_roles(['admin', 'teacher'])
def cancel_text_delivery(delivery_id):
    """テキスト配信のキャンセル"""
    try:
        delivery = TextDelivery.query.get_or_404(delivery_id)
        text_set = delivery.text_set
        
        # 権限チェック
        if current_user.role == 'teacher' and text_set.school_id != current_user.school_id:
            flash('この配信をキャンセルする権限がありません。', 'error')
            return redirect(url_for('texts.text_sets'))
        
        # 配信記録を削除
        db.session.delete(delivery)
        db.session.commit()
        
        log_activity("text_delivery_cancelled", f"Cancelled delivery {delivery_id}")
        flash('テキスト配信をキャンセルしました。', 'success')
        
        return redirect(url_for('texts.text_sets'))
        
    except Exception as e:
        current_app.logger.error(f"Cancel text delivery error: {str(e)}")
        db.session.rollback()
        flash('配信のキャンセル中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.text_sets'))