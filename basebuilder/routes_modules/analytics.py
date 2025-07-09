"""
BaseBuilder Analytics Routes
============================
分析・統計に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /analysis (GET)
- /analysis/<int:class_id> (GET)
- /analysis/student/<int:student_id> (GET)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from extensions import db
from app.models import User
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, AnswerRecord, 
    ProficiencyRecord, TextSet, TextDelivery, WordProficiency
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/basebuilder')

@analytics_bp.route('/analytics')
@login_required
def analytics():
    """分析機能のメイン画面"""
    if current_user.role == 'student':
        return redirect(url_for('analytics.student_analytics'))
    else:
        return redirect(url_for('analytics.teacher_analytics'))

@analytics_bp.route('/teacher_analytics')
@login_required
def teacher_analytics():
    """教師向け分析ダッシュボード"""
    try:
        if current_user.role not in ['admin', 'teacher']:
            flash('分析機能は教師・管理者のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # 全体統計の取得
        total_students = User.query.filter_by(role='student').count()
        total_problems = BasicKnowledgeItem.query.filter_by(is_active=True).count()
        total_categories = ProblemCategory.query.count()
        total_texts = TextSet.query.count()
        
        # 最近の活動統計
        from datetime import datetime, timedelta
        last_week = datetime.now() - timedelta(days=7)
        
        recent_answers = AnswerRecord.query.filter(
            AnswerRecord.created_at >= last_week
        ).count()
        
        active_students = db.session.query(AnswerRecord.student_id).filter(
            AnswerRecord.created_at >= last_week
        ).distinct().count()
        
        # カテゴリ別の問題数統計
        category_stats = db.session.query(
            ProblemCategory.name,
            db.func.count(BasicKnowledgeItem.id).label('problem_count')
        ).join(
            BasicKnowledgeItem, BasicKnowledgeItem.category_id == ProblemCategory.id
        ).group_by(ProblemCategory.id).all()
        
        # 最近の学習活動
        recent_activities = AnswerRecord.query.join(
            BasicKnowledgeItem
        ).join(
            User, AnswerRecord.student_id == User.id
        ).order_by(
            AnswerRecord.created_at.desc()
        ).limit(10).all()
        
        return render_template('basebuilder/teacher_analytics.html',
                             total_students=total_students,
                             total_problems=total_problems,
                             total_categories=total_categories,
                             total_texts=total_texts,
                             recent_answers=recent_answers,
                             active_students=active_students,
                             category_stats=category_stats,
                             recent_activities=recent_activities)
        
    except Exception as e:
        current_app.logger.error(f"Teacher analytics error: {str(e)}")
        flash('分析データの取得中にエラーが発生しました。', 'error')
        return redirect(url_for('basebuilder.index'))

@analytics_bp.route('/student_analytics')
@login_required
def student_analytics():
    """学生向け分析ダッシュボード"""
    try:
        if current_user.role != 'student':
            flash('学生分析機能は学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # 学生の学習統計
        total_answers = AnswerRecord.query.filter_by(student_id=current_user.id).count()
        correct_answers = AnswerRecord.query.filter_by(
            student_id=current_user.id, is_correct=True
        ).count()
        
        accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        
        # カテゴリ別の成績
        category_performance = db.session.query(
            ProblemCategory.name,
            db.func.count(AnswerRecord.id).label('total'),
            db.func.sum(db.case((AnswerRecord.is_correct == True, 1), else_=0)).label('correct')
        ).join(
            BasicKnowledgeItem, BasicKnowledgeItem.category_id == ProblemCategory.id
        ).join(
            AnswerRecord, AnswerRecord.problem_id == BasicKnowledgeItem.id
        ).filter(
            AnswerRecord.student_id == current_user.id
        ).group_by(ProblemCategory.id).all()
        
        # 習熟度記録
        proficiency_records = ProficiencyRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        # 最近の学習履歴
        recent_answers = AnswerRecord.query.filter_by(
            student_id=current_user.id
        ).order_by(AnswerRecord.created_at.desc()).limit(20).all()
        
        return render_template('basebuilder/student_analytics.html',
                             total_answers=total_answers,
                             correct_answers=correct_answers,
                             accuracy=round(accuracy, 1),
                             category_performance=category_performance,
                             proficiency_records=proficiency_records,
                             recent_answers=recent_answers)
        
    except Exception as e:
        current_app.logger.error(f"Student analytics error: {str(e)}")
        flash('学習分析データの取得中にエラーが発生しました。', 'error')
        return redirect(url_for('basebuilder.index'))


@analytics_bp.route('/analysis')
@analytics_bp.route('/analysis/<int:class_id>')
@login_required
def analysis(class_id=None):
    """教師向け分析ダッシュボード"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('analytics.analysis'))
        
        current_app.logger.info(f"Analysis dashboard accessed by teacher {current_user.id}")
        
        # 教師が担当するクラスを取得
        classes = getattr(current_user, 'classes_teaching', [])
        
        selected_class = None
        class_students = []
        student_progress = {}
        student_last_activity = {}
        
        if class_id and classes:
            # 選択されたクラスを取得
            for class_obj in classes:
                if class_obj.id == class_id:
                    selected_class = class_obj
                    break
            
            if selected_class:
                # クラスの学生を取得
                class_students = selected_class.students.all()
                
                # 各学生の進捗率とアクティビティを計算
                for student in class_students:
                    # 学生の熟練度記録を取得
                    proficiency_records = ProficiencyRecord.query.filter_by(
                        student_id=student.id
                    ).all()
                    
                    # 総合進捗率を計算（カテゴリごとの熟練度の平均）
                    if proficiency_records:
                        total_level = sum(record.level for record in proficiency_records)
                        avg_level = total_level / len(proficiency_records)
                        # 5段階を100%に変換
                        progress = (avg_level / 5) * 100
                        student_progress[student.id] = round(progress)
                    else:
                        student_progress[student.id] = 0
                    
                    # 最後の活動日時を取得
                    last_answer = AnswerRecord.query.filter_by(
                        student_id=student.id
                    ).order_by(AnswerRecord.created_at.desc()).first()
                    
                    if last_answer:
                        student_last_activity[student.id] = last_answer.created_at
        
        return render_template(
            'basebuilder/analysis.html',
            classes=classes,
            selected_class=selected_class,
            class_students=class_students,
            student_progress=student_progress,
            student_last_activity=student_last_activity
        )
        
    except Exception as e:
        current_app.logger.error(f"Analysis dashboard error: {str(e)}")
        flash('分析ダッシュボードの読み込み中にエラーが発生しました。')
        return redirect(url_for('analytics.analysis'))


@analytics_bp.route('/analysis/student/<int:student_id>')
@login_required
def student_analysis(student_id):
    """個別学生分析"""
    try:
        if current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('analytics.analysis'))
        
        current_app.logger.info(f"Student analysis accessed by teacher {current_user.id} for student {student_id}")
        
        # 学生を取得
        student = User.query.get_or_404(student_id)
        
        # 学生がクラスに所属しているか確認
        student_in_class = False
        for class_obj in current_user.classes_teaching:
            if student in class_obj.students:
                student_in_class = True
                break
        
        if not student_in_class:
            flash('この学生の情報を閲覧する権限がありません。')
            return redirect(url_for('analytics.analysis'))
        
        # 学生が所属するクラスを取得
        enrolled_class_ids = [c.id for c in student.enrolled_classes]
        
        # 配信されたテキストを取得
        delivered_text_ids = db.session.query(TextDelivery.text_set_id).filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).distinct().all()
        delivered_text_ids = [t[0] for t in delivered_text_ids]
        
        # 配信されたテキストを取得
        text_sets = TextSet.query.filter(
            TextSet.id.in_(delivered_text_ids)
        ).all()
        
        # テキストごとの定着度データを収集
        category_proficiency = {}
        text_proficiency_data = {}
        total_words = 0
        mastered_words = 0
        
        for text in text_sets:
            # テキスト内の単語（問題）を取得
            problems = BasicKnowledgeItem.query.filter_by(
                text_set_id=text.id,
                is_active=True
            ).all()
            
            if not problems:
                continue
                
            # このテキストの単語数をカウント
            text_words_count = len(problems)
            total_words += text_words_count
            
            # 単語IDのリストを作成
            problem_ids = [p.id for p in problems]
            
            # カテゴリ情報
            category_id = text.category_id
            
            # 単語ごとの熟練度を取得
            word_proficiencies = WordProficiency.query.filter(
                WordProficiency.student_id == student_id,
                WordProficiency.problem_id.in_(problem_ids)
            ).all()
            
            # レベルごとの単語数をカウント
            level_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
            # 単語マップを作成（存在する単語の熟練度）
            proficiency_map = {}
            
            for wp in word_proficiencies:
                proficiency_map[wp.problem_id] = wp.level
                level_counts[wp.level] += 1
            
            # 未学習の単語をカウント
            for pid in problem_ids:
                if pid not in proficiency_map:
                    level_counts[0] += 1
            
            # このカテゴリのマスター単語数
            text_mastered = level_counts[5]
            mastered_words += text_mastered
            
            # テキストの定着度を計算
            max_points = text_words_count * 5  # 最大ポイント
            actual_points = sum(level * count for level, count in level_counts.items() if level > 0)
            
            # 最終更新日を取得
            updated_at = None
            if word_proficiencies:
                updated_at = max(wp.updated_at for wp in word_proficiencies)
            
            # テキストの定着度をパーセントで計算
            text_percentage = (actual_points / max_points * 100) if max_points > 0 else 0
            
            # テキスト定着度データを保存
            text_proficiency_data[text.id] = {
                'level': round(text_percentage),
                'updated_at': updated_at
            }
            
            # カテゴリ定着度データを更新/作成
            if category_id in category_proficiency:
                # 既存のカテゴリデータを更新
                category_proficiency[category_id]['total'] += text_words_count
                category_proficiency[category_id]['mastered'] += text_mastered
                
                # レベルカウントを更新
                for level, count in level_counts.items():
                    if level in category_proficiency[category_id]['levels']:
                        category_proficiency[category_id]['levels'][level] += count
                    else:
                        category_proficiency[category_id]['levels'][level] = count
                
                # 最終更新日を更新
                if updated_at and (not category_proficiency[category_id]['updated_at'] or 
                                    updated_at > category_proficiency[category_id]['updated_at']):
                    category_proficiency[category_id]['updated_at'] = updated_at
                    
            else:
                # 新しいカテゴリデータを作成
                category_proficiency[category_id] = {
                    'category': text.category,
                    'text_set_id': text.id,  # 最初のテキストIDを保存
                    'total': text_words_count,
                    'mastered': text_mastered,
                    'levels': level_counts,
                    'updated_at': updated_at
                }
        
        # 各カテゴリの定着度パーセントを計算
        for category_data in category_proficiency.values():
            max_points = category_data['total'] * 5
            actual_points = sum(level * count for level, count in category_data['levels'].items() if level > 0)
            category_data['percentage'] = (actual_points / max_points * 100) if max_points > 0 else 0
        
        # 総合定着度を計算
        overall_proficiency = 0
        if total_words > 0:
            # 総合ポイント
            total_possible_points = total_words * 5
            total_actual_points = sum(
                sum(level * count for level, count in cat_data['levels'].items() if level > 0)
                for cat_data in category_proficiency.values()
            )
            overall_proficiency = (total_actual_points / total_possible_points * 100) if total_possible_points > 0 else 0
        
        # 習得率
        mastery_rate = (mastered_words / total_words * 100) if total_words > 0 else 0
        
        # 学生の解答履歴を取得（最新20件）
        answer_records = AnswerRecord.query.filter_by(
            student_id=student_id
        ).order_by(AnswerRecord.created_at.desc()).limit(20).all()
        
        # 解答数と正解率を計算
        all_answers = AnswerRecord.query.filter_by(student_id=student_id).all()
        answer_count = len(all_answers)
        correct_count = sum(1 for answer in all_answers if answer.is_correct)
        correct_rate = (correct_count / answer_count * 100) if answer_count > 0 else 0
        
        # 最後の活動日時
        last_activity = answer_records[0].created_at if answer_records else None
        
        # 単語ごとの熟練度を取得（解答履歴表示用）
        word_proficiency = {}
        
        # 解答履歴に含まれる問題IDを収集
        problem_ids = [record.problem_id for record in answer_records]
        
        # 熟練度レコードを取得
        word_prof_records = WordProficiency.query.filter(
            WordProficiency.student_id == student_id,
            WordProficiency.problem_id.in_(problem_ids)
        ).all()
        
        # 辞書にマッピング
        for wp in word_prof_records:
            word_proficiency[wp.problem_id] = {
                'level': wp.level,
                'updated_at': wp.updated_at,
                'review_date': wp.review_date
            }
        
        return render_template(
            'basebuilder/student_analysis.html',
            student=student,
            proficiency_records=None,  # 古い熟練度記録は不要
            answer_records=answer_records,
            overall_proficiency=overall_proficiency,
            category_proficiency=category_proficiency,
            text_proficiency=text_proficiency_data,
            total_words=total_words,
            mastered_words=mastered_words,
            mastery_rate=mastery_rate,
            correct_rate=correct_rate,
            answer_count=answer_count,
            last_activity=last_activity,
            word_proficiency=word_proficiency
        )
        
    except Exception as e:
        current_app.logger.error(f"Student analysis error: {str(e)}")
        flash('学生分析データの取得中にエラーが発生しました。')
        return redirect(url_for('analytics.analysis'))