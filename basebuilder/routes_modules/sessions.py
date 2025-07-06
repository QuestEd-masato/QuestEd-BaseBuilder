"""
BaseBuilder Sessions Routes
===========================
学習セッション管理に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /start_session (GET)
- /category/<int:category_id>/start_session (GET)
- /text/<int:text_id>/start_session (GET)
- /next_problem (GET, POST)
- /session_summary (GET)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import random
import json

from extensions import db
from sqlalchemy import func
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, AnswerRecord, 
    ProficiencyRecord, TextSet, WordProficiency
)

sessions_bp = Blueprint('sessions', __name__, url_prefix='/basebuilder')

@sessions_bp.route('/debug/auth')
def debug_auth():
    """認証状態のデバッグ表示"""
    if not current_app.debug:
        return "Debug mode only", 404
    
    debug_info = {
        'is_authenticated': current_user.is_authenticated if current_user else False,
        'user_id': current_user.id if current_user and current_user.is_authenticated else None,
        'role': current_user.role if current_user and current_user.is_authenticated else None,
        'session_keys': list(session.keys()) if session else []
    }
    
    return f"<pre>{json.dumps(debug_info, indent=2)}</pre>"


@sessions_bp.route('/start_session')
@login_required
def start_session():
    """全体学習セッション開始"""
    try:
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # セッション初期化
        session.clear()
        session['session_type'] = 'general'
        session['start_time'] = datetime.now().isoformat()
        session['problems_answered'] = 0
        session['correct_answers'] = 0
        session['current_problem_index'] = 0
        
        # 学習可能な問題を取得（学生の習熟度に基づく）
        available_problems = _get_adaptive_problems(current_user.id)
        
        if not available_problems:
            flash('現在利用可能な問題がありません。')
            return redirect(url_for('basebuilder.index'))
        
        # 問題IDをセッションに保存
        session['problem_ids'] = [p.id for p in available_problems]
        session['total_problems'] = len(available_problems)
        
        current_app.logger.info(f"General session started by user {current_user.id}")
        flash(f'{len(available_problems)}問の学習セッションを開始します。', 'info')
        
        return redirect(url_for('sessions.next_problem'))
        
    except Exception as e:
        current_app.logger.error(f"Start session error: {str(e)}")
        flash('学習セッションの開始中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))


@sessions_bp.route('/category/<int:category_id>/start_session')
@login_required
def start_category_session(category_id):
    """カテゴリ別学習セッション開始"""
    try:
        current_app.logger.info(f"Session start attempt: user={current_user.id if current_user.is_authenticated else 'anonymous'}, category={category_id}")
        
        if not current_user.is_authenticated:
            current_app.logger.warning(f"Unauthenticated access to session start: category={category_id}")
            flash('ログインが必要です。')
            return redirect(url_for('auth.login'))
            
        if current_user.role != 'student':
            current_app.logger.warning(f"Non-student access to session: user={current_user.id}, role={current_user.role}")
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        category = ProblemCategory.query.get_or_404(category_id)
        
        # セッション初期化
        session.clear()
        session['session_type'] = 'category'
        session['category_id'] = category_id
        session['start_time'] = datetime.now().isoformat()
        session['problems_answered'] = 0
        session['correct_answers'] = 0
        session['current_problem_index'] = 0
        
        # カテゴリ内の問題を取得
        category_problems = BasicKnowledgeItem.query.filter_by(
            category_id=category_id,
            is_active=True
        ).order_by(BasicKnowledgeItem.difficulty).all()
        
        if not category_problems:
            flash(f'カテゴリ「{category.name}」には現在利用可能な問題がありません。')
            return redirect(url_for('categories.categories'))
        
        # 問題をシャッフル（適応的学習のため）
        random.shuffle(category_problems)
        
        session['problem_ids'] = [p.id for p in category_problems]
        session['total_problems'] = len(category_problems)
        
        current_app.logger.info(f"Category {category_id} session started by user {current_user.id}")
        flash(f'カテゴリ「{category.name}」の学習セッション（{len(category_problems)}問）を開始します。', 'info')
        
        return redirect(url_for('sessions.next_problem'))
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Start category session error: {str(e)}")
        current_app.logger.error(f"Full traceback: {error_details}")
        flash(f'カテゴリ学習セッションの開始中にエラーが発生しました: {str(e)}')
        return redirect(url_for('categories.categories'))


@sessions_bp.route('/text/<int:text_id>/start_session')
@login_required
def start_text_session(text_id):
    """テキスト別学習セッション開始"""
    try:
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        text_set = TextSet.query.get_or_404(text_id)
        
        # セッション初期化
        session.clear()
        session['session_type'] = 'text'
        session['text_id'] = text_id
        session['start_time'] = datetime.now().isoformat()
        session['problems_answered'] = 0
        session['correct_answers'] = 0
        session['current_problem_index'] = 0
        
        # テキスト内の問題を取得
        text_problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id,
            is_active=True
        ).order_by(BasicKnowledgeItem.difficulty).all()
        
        if not text_problems:
            flash(f'テキスト「{text_set.title}」には現在利用可能な問題がありません。')
            return redirect(url_for('categories.category_texts', category_id=text_set.category_id))
        
        session['problem_ids'] = [p.id for p in text_problems]
        session['total_problems'] = len(text_problems)
        
        current_app.logger.info(f"Text {text_id} session started by user {current_user.id}")
        flash(f'テキスト「{text_set.title}」の学習セッション（{len(text_problems)}問）を開始します。', 'info')
        
        return redirect(url_for('sessions.next_problem'))
        
    except Exception as e:
        current_app.logger.error(f"Start text session error: {str(e)}")
        flash('テキスト学習セッションの開始中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))


@sessions_bp.route('/next_problem', methods=['GET', 'POST'])
@login_required
def next_problem():
    """次の問題表示・回答処理"""
    try:
        current_app.logger.info(f"Next problem request: user={current_user.id if current_user.is_authenticated else 'anonymous'}, method={request.method}")
        
        if not current_user.is_authenticated:
            current_app.logger.warning("Unauthenticated access to next_problem")
            flash('ログインが必要です。')
            return redirect(url_for('auth.login'))
            
        if current_user.role != 'student':
            current_app.logger.warning(f"Non-student access to next_problem: user={current_user.id}, role={current_user.role}")
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # セッション情報の確認
        current_app.logger.info(f"Session data keys: {list(session.keys())}")
        if 'problem_ids' not in session:
            current_app.logger.warning("No problem_ids in session, redirecting to start new session")
            flash('学習セッションが見つかりません。新しいセッションを開始してください。')
            return redirect(url_for('basebuilder.index'))
        
        problem_ids = session['problem_ids']
        current_index = session.get('current_problem_index', 0)
        
        # POST リクエスト（回答処理）
        if request.method == 'POST':
            problem_id = request.form.get('problem_id', type=int)
            user_answer = request.form.get('answer', '').strip()
            start_time = request.form.get('start_time')
            
            if problem_id and user_answer:
                _process_answer(problem_id, user_answer, start_time)
                session['current_problem_index'] = current_index + 1
                session['problems_answered'] = session.get('problems_answered', 0) + 1
        
        # セッション完了チェック
        current_index = session.get('current_problem_index', 0)
        if current_index >= len(problem_ids):
            return redirect(url_for('sessions.session_summary'))
        
        # 次の問題を取得
        next_problem_id = problem_ids[current_index]
        problem = BasicKnowledgeItem.query.get_or_404(next_problem_id)
        
        # 進捗情報
        progress = {
            'current': current_index + 1,
            'total': len(problem_ids),
            'percentage': round((current_index / len(problem_ids)) * 100, 1)
        }
        
        # 選択肢の処理
        options = []
        if problem.options:
            try:
                options = json.loads(problem.options)
            except:
                options = []
        
        return render_template('basebuilder/problem_session.html',
                             problem=problem,
                             options=options,
                             progress=progress,
                             session_info=session)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Next problem error: {str(e)}")
        current_app.logger.error(f"Full traceback: {error_details}")
        flash(f'問題表示中にエラーが発生しました: {str(e)}')
        return redirect(url_for('basebuilder.index'))


@sessions_bp.route('/solve_text/<int:text_id>')
@login_required
def solve_text(text_id):
    """テキスト問題解答セッション開始"""
    try:
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。', 'error')
            return redirect(url_for('basebuilder.index'))
        
        # テキストセットを取得
        text_set = TextSet.query.get_or_404(text_id)
        
        # アクセス権限チェック（配信されたテキストか確認）
        from app.models import ClassEnrollment
        from basebuilder.models import TextDelivery
        
        enrolled_class_ids = [enrollment.class_id for enrollment in 
                            ClassEnrollment.query.filter_by(
                                student_id=current_user.id,
                                is_active=True
                            ).all()]
        
        delivery_exists = TextDelivery.query.filter(
            TextDelivery.text_set_id == text_id,
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).first()
        
        if not delivery_exists:
            flash('このテキストにアクセスする権限がありません。', 'error')
            return redirect(url_for('texts.my_texts'))
        
        # テキストの問題を取得
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id
        ).order_by(BasicKnowledgeItem.order_in_text).all()
        
        if not problems:
            flash('このテキストには問題が登録されていません。', 'warning')
            return redirect(url_for('texts.my_texts'))
        
        # セッション初期化
        session.clear()
        session['session_type'] = 'text'
        session['text_id'] = text_id
        session['start_time'] = datetime.now().isoformat()
        session['problems_answered'] = 0
        session['correct_answers'] = 0
        session['current_problem_index'] = 0
        session['problem_ids'] = [p.id for p in problems]
        
        # 最初の問題に進む
        return redirect(url_for('sessions.solve_problem', problem_id=problems[0].id))
        
    except Exception as e:
        current_app.logger.error(f"Solve text error: {str(e)}")
        flash('テキスト学習の開始中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.my_texts'))


@sessions_bp.route('/solve_problem/<int:problem_id>')
@login_required
def solve_problem(problem_id):
    """個別問題表示・解答画面"""
    try:
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。', 'error')
            return redirect(url_for('basebuilder.index'))
        
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # 進捗情報を計算
        progress = {}
        if 'problem_ids' in session and session['problem_ids']:
            problem_ids = session['problem_ids']
            try:
                current_index = problem_ids.index(problem_id)
                progress = {
                    'current': current_index + 1,
                    'total': len(problem_ids),
                    'percentage': round(((current_index + 1) / len(problem_ids)) * 100, 1)
                }
            except ValueError:
                progress = {'current': 1, 'total': 1, 'percentage': 100}
        else:
            progress = {'current': 1, 'total': 1, 'percentage': 100}
        
        # 選択肢の処理
        options = []
        if problem.choices:
            try:
                options = json.loads(problem.choices)
            except:
                options = []
        
        # 過去の回答履歴を取得
        past_answers = AnswerRecord.query.filter_by(
            student_id=current_user.id,
            problem_id=problem_id
        ).order_by(AnswerRecord.created_at.desc()).limit(3).all()
        
        return render_template('basebuilder/solve_problem.html',
                             problem=problem,
                             options=options,
                             progress=progress,
                             past_answers=past_answers,
                             session_info=session)
        
    except Exception as e:
        current_app.logger.error(f"Solve problem error: {str(e)}")
        flash('問題表示中にエラーが発生しました。', 'error')
        return redirect(url_for('texts.my_texts'))


@sessions_bp.route('/submit_answer/<int:problem_id>', methods=['POST'])
@login_required
def submit_answer(problem_id):
    """問題回答提出処理"""
    try:
        if current_user.role != 'student':
            return jsonify({'success': False, 'message': 'アクセス権限がありません。'})
        
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        student_answer = request.form.get('answer', '').strip()
        
        if not student_answer:
            return jsonify({'success': False, 'message': '回答を入力してください。'})
        
        # 正解判定
        is_correct = _check_answer(problem, student_answer)
        
        # 回答記録を保存
        answer_record = AnswerRecord(
            student_id=current_user.id,
            problem_id=problem_id,
            student_answer=student_answer,
            is_correct=is_correct,
            created_at=datetime.utcnow()
        )
        
        db.session.add(answer_record)
        
        # セッション統計を更新
        if 'problems_answered' in session:
            session['problems_answered'] += 1
            if is_correct:
                session['correct_answers'] += 1
        
        # 単語習熟度の更新（英単語の場合）
        if problem.category and '英単語' in problem.category.name:
            _update_word_proficiency(current_user.id, problem, is_correct)
        
        db.session.commit()
        
        # 次の問題のURLを決定
        next_url = None
        if 'problem_ids' in session and session['problem_ids']:
            try:
                current_index = session['problem_ids'].index(problem_id)
                if current_index + 1 < len(session['problem_ids']):
                    next_problem_id = session['problem_ids'][current_index + 1]
                    next_url = url_for('sessions.solve_problem', problem_id=next_problem_id)
                else:
                    # 最後の問題の場合
                    next_url = url_for('sessions.session_summary')
            except ValueError:
                next_url = url_for('sessions.session_summary')
        else:
            next_url = url_for('sessions.session_summary')
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'correct_answer': problem.correct_answer,
            'explanation': problem.explanation,
            'next_url': next_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Submit answer error: {str(e)}")
        return jsonify({'success': False, 'message': 'サーバーエラーが発生しました。'})


@sessions_bp.route('/session_summary')
@login_required
def session_summary():
    """学習セッション結果表示"""
    try:
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # セッション情報の確認
        if 'start_time' not in session:
            flash('セッション情報が見つかりません。')
            return redirect(url_for('basebuilder.index'))
        
        # セッション統計を計算
        start_time = datetime.fromisoformat(session['start_time'])
        end_time = datetime.now()
        duration = end_time - start_time
        
        problems_answered = session.get('problems_answered', 0)
        correct_answers = session.get('correct_answers', 0)
        accuracy = (correct_answers / problems_answered * 100) if problems_answered > 0 else 0
        
        # 習熟度の更新
        _update_proficiency_after_session(current_user.id, session)
        
        summary = {
            'session_type': session.get('session_type', 'general'),
            'duration_minutes': round(duration.total_seconds() / 60, 1),
            'problems_answered': problems_answered,
            'correct_answers': correct_answers,
            'accuracy': round(accuracy, 1),
            'start_time': start_time,
            'end_time': end_time
        }
        
        # カテゴリまたはテキスト情報
        if session.get('category_id'):
            category = ProblemCategory.query.get(session['category_id'])
            summary['category'] = category
        
        if session.get('text_id'):
            text_set = TextSet.query.get(session['text_id'])
            summary['text_set'] = text_set
        
        current_app.logger.info(f"Session completed by user {current_user.id}: {problems_answered} problems, {accuracy}% accuracy")
        
        # セッションクリア
        session.clear()
        
        return render_template('basebuilder/session_summary.html',
                             summary=summary)
        
    except Exception as e:
        current_app.logger.error(f"Session summary error: {str(e)}")
        flash('セッション結果の表示中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))


def _get_adaptive_problems(student_id, limit=20):
    """適応的学習のための問題選択"""
    try:
        # 学生の習熟度を取得
        proficiency_records = ProficiencyRecord.query.filter_by(
            student_id=student_id
        ).all()
        
        weak_categories = []
        for record in proficiency_records:
            if record.level < 3:  # レベル3未満を弱点とする
                weak_categories.append(record.category_id)
        
        # 弱点がある場合はそのカテゴリから優先的に出題
        if weak_categories:
            problems = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.category_id.in_(weak_categories),
                BasicKnowledgeItem.is_active == True
            ).order_by(BasicKnowledgeItem.difficulty).limit(limit).all()
        else:
            # 弱点がない場合は全体からランダム選択
            problems = BasicKnowledgeItem.query.filter_by(
                is_active=True
            ).order_by(func.random()).limit(limit).all()
        
        return problems
        
    except Exception as e:
        current_app.logger.error(f"Adaptive problems selection error: {str(e)}")
        return []


def _process_answer(problem_id, user_answer, start_time):
    """回答処理"""
    try:
        problem = BasicKnowledgeItem.query.get(problem_id)
        if not problem:
            return
        
        # 回答時間計算
        response_time = 0
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                response_time = (datetime.now() - start_dt).total_seconds()
            except:
                pass
        
        # 正解判定
        is_correct = user_answer.strip().lower() == problem.correct_answer.strip().lower()
        
        # 回答記録を保存
        answer_record = AnswerRecord(
            student_id=current_user.id,
            problem_id=problem_id,
            student_answer=user_answer,
            is_correct=is_correct,
            response_time=response_time,
            created_at=datetime.utcnow()
        )
        
        db.session.add(answer_record)
        db.session.commit()
        
        # セッション統計更新
        if is_correct:
            session['correct_answers'] = session.get('correct_answers', 0) + 1
        
        current_app.logger.info(f"Answer processed: user {current_user.id}, problem {problem_id}, correct: {is_correct}")
        
    except Exception as e:
        current_app.logger.error(f"Process answer error: {str(e)}")
        db.session.rollback()


def _update_proficiency_after_session(student_id, session_data):
    """セッション後の習熟度更新"""
    try:
        session_type = session_data.get('session_type')
        
        if session_type == 'category' and 'category_id' in session_data:
            category_id = session_data['category_id']
            accuracy = session_data.get('correct_answers', 0) / max(session_data.get('problems_answered', 1), 1)
            
            # カテゴリの習熟度更新
            proficiency = ProficiencyRecord.query.filter_by(
                student_id=student_id,
                category_id=category_id
            ).first()
            
            if proficiency:
                # 既存レコードの更新
                level_change = 0.2 if accuracy > 0.8 else -0.1 if accuracy < 0.5 else 0
                proficiency.level = max(0, min(5, proficiency.level + level_change))
                proficiency.updated_at = datetime.utcnow()
            else:
                # 新規レコード作成
                initial_level = 2.0 if accuracy > 0.7 else 1.0
                proficiency = ProficiencyRecord(
                    student_id=student_id,
                    category_id=category_id,
                    level=initial_level,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(proficiency)
            
            db.session.commit()
            
    except Exception as e:
        current_app.logger.error(f"Update proficiency error: {str(e)}")
        db.session.rollback()


def _check_answer(problem, student_answer):
    """回答の正誤判定"""
    try:
        student_answer = student_answer.strip()
        correct_answer = problem.correct_answer.strip()
        
        # 複数の正解パターンがある場合（カンマ区切り）
        if ',' in correct_answer:
            correct_answers = [ans.strip().lower() for ans in correct_answer.split(',')]
            return student_answer.lower() in correct_answers
        
        # 単一の正解
        return student_answer.lower() == correct_answer.lower()
        
    except Exception as e:
        current_app.logger.error(f"Check answer error: {str(e)}")
        return False


def _update_word_proficiency(student_id, problem, is_correct):
    """単語習熟度の更新"""
    try:
        # 問題が単語問題の場合のみ更新
        if not problem.title or len(problem.title.split()) > 3:
            return
        
        word = problem.title.strip().lower()
        
        # 既存の習熟度記録を取得
        proficiency = WordProficiency.query.filter_by(
            student_id=student_id,
            word=word
        ).first()
        
        if not proficiency:
            # 新規作成
            proficiency = WordProficiency(
                student_id=student_id,
                word=word,
                correct_count=1 if is_correct else 0,
                total_count=1,
                level=80 if is_correct else 20,
                last_studied_at=datetime.utcnow()
            )
            db.session.add(proficiency)
        else:
            # 既存レコード更新
            proficiency.total_count += 1
            if is_correct:
                proficiency.correct_count += 1
            
            # 習熟度レベル再計算
            accuracy = proficiency.correct_count / proficiency.total_count
            if accuracy >= 0.9:
                proficiency.level = min(100, proficiency.level + 10)
            elif accuracy >= 0.7:
                proficiency.level = min(100, proficiency.level + 5)
            elif accuracy < 0.5:
                proficiency.level = max(0, proficiency.level - 5)
            
            proficiency.last_studied_at = datetime.utcnow()
        
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Update word proficiency error: {str(e)}")
        db.session.rollback()