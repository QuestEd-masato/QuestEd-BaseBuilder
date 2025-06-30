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
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, AnswerRecord, 
    ProficiencyRecord, TextSet, WordProficiency
)

sessions_bp = Blueprint('sessions', __name__)


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
        if current_user.role != 'student':
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
        current_app.logger.error(f"Start category session error: {str(e)}")
        flash('カテゴリ学習セッションの開始中にエラーが発生しました。')
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
        if current_user.role != 'student':
            flash('学習セッションは学生のみアクセス可能です。')
            return redirect(url_for('basebuilder.index'))
        
        # セッション情報の確認
        if 'problem_ids' not in session:
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
        current_app.logger.error(f"Next problem error: {str(e)}")
        flash('問題表示中にエラーが発生しました。')
        return redirect(url_for('basebuilder.index'))


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