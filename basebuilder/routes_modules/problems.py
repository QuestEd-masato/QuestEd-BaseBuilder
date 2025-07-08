"""
BaseBuilder Problems Routes
===========================
問題管理に関するルートハンドラ

移行元: basebuilder/routes.py の以下のルート:
- /problems (GET)
- /problem/create (GET, POST)
- /problem/<int:problem_id>/edit (GET, POST)
- /start_search_session (GET)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from extensions import db
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, AnswerRecord, 
    ProficiencyRecord, TextSet
)
from basebuilder.utils import require_roles

problems_bp = Blueprint('problems', __name__, url_prefix='/basebuilder')


@problems_bp.route('/problems')
@login_required
def problems():
    """問題一覧表示"""
    try:
        current_app.logger.info(f"Problems list accessed by user {current_user.id}")
        
        # クエリパラメータの取得
        category_id = request.args.get('category_id', type=int)
        text_id = request.args.get('text_id', type=int)
        difficulty = request.args.get('difficulty', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 基本クエリ
        query = BasicKnowledgeItem.query
        
        # フィルタリング
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if text_id:
            query = query.filter_by(text_set_id=text_id)
        
        if difficulty:
            query = query.filter_by(difficulty=difficulty)
        
        # ページネーション
        problems_pagination = query.order_by(
            BasicKnowledgeItem.created_at.desc()
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # カテゴリとテキストセット情報を取得
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        text_sets = TextSet.query.order_by(TextSet.title).all()
        
        # 学生の場合、自分の回答記録と習熟度を取得
        user_answers = {}
        word_proficiencies = {}
        if current_user.role == 'student':
            answer_records = AnswerRecord.query.filter_by(
                student_id=current_user.id
            ).all()
            
            for record in answer_records:
                if record.problem_id not in user_answers:
                    user_answers[record.problem_id] = []
                user_answers[record.problem_id].append(record)
            
            # 単語習熟度記録を取得
            from basebuilder.models import WordProficiency
            proficiency_records = WordProficiency.query.filter_by(
                student_id=current_user.id
            ).all()
            
            for record in proficiency_records:
                word_proficiencies[record.problem_id] = record
        
        return render_template('basebuilder/problems.html',
                             problems=problems_pagination.items,
                             pagination=problems_pagination,
                             categories=categories,
                             text_sets=text_sets,
                             user_answers=user_answers,
                             word_proficiencies=word_proficiencies,
                             selected_category=category_id,
                             selected_text=text_id,
                             selected_difficulty=difficulty)
        
    except Exception as e:
        current_app.logger.error(f"Problems list error: {str(e)}")
        flash('問題一覧の取得中にエラーが発生しました。')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/problem/create', methods=['GET', 'POST'])
@login_required
def create_problem():
    """問題作成"""
    try:
        if current_user.role not in ['admin', 'teacher']:
            flash('問題の作成権限がありません。')
            return redirect(url_for('problems.problems'))
        
        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            options = request.form.get('options', '').strip()
            correct_answer = request.form.get('correct_answer', '').strip()
            explanation = request.form.get('explanation', '').strip()
            category_id = request.form.get('category_id', type=int)
            text_set_id = request.form.get('text_set_id', type=int)
            difficulty_level = request.form.get('difficulty_level', type=int)
            
            # 入力値検証
            if not content:
                flash('問題文を入力してください。', 'error')
                return render_template('basebuilder/create_problem.html',
                                     categories=ProblemCategory.query.all(),
                                     text_sets=TextSet.query.all())
            
            if not correct_answer:
                flash('正解を入力してください。', 'error')
                return render_template('basebuilder/create_problem.html',
                                     categories=ProblemCategory.query.all(),
                                     text_sets=TextSet.query.all())
            
            if not category_id:
                flash('カテゴリを選択してください。', 'error')
                return render_template('basebuilder/create_problem.html',
                                     categories=ProblemCategory.query.all(),
                                     text_sets=TextSet.query.all())
            
            # 選択肢のJSON変換
            options_list = []
            if options:
                try:
                    # 改行区切りの選択肢をリストに変換
                    options_list = [opt.strip() for opt in options.split('\n') if opt.strip()]
                except:
                    flash('選択肢の形式が正しくありません。', 'error')
                    return render_template('basebuilder/create_problem.html',
                                         categories=ProblemCategory.query.all(),
                                         text_sets=TextSet.query.all())
            
            # 新しい問題を作成
            new_problem = BasicKnowledgeItem(
                content=content,
                options=json.dumps(options_list, ensure_ascii=False) if options_list else None,
                correct_answer=correct_answer,
                explanation=explanation,
                category_id=category_id,
                text_set_id=text_set_id if text_set_id else None,
                difficulty=difficulty_level or 1,
                created_by=current_user.id,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            try:
                db.session.add(new_problem)
                db.session.commit()
                
                current_app.logger.info(f"Problem created by user {current_user.id}")
                flash('問題を作成しました。', 'success')
                return redirect(url_for('problems.problems'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Problem creation error: {str(e)}")
                flash('問題の作成に失敗しました。', 'error')
        
        # GET リクエストの場合
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        text_sets = TextSet.query.order_by(TextSet.title).all()
        
        return render_template('basebuilder/create_problem.html',
                             categories=categories,
                             text_sets=text_sets)
        
    except Exception as e:
        current_app.logger.error(f"Create problem error: {str(e)}")
        flash('問題作成画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/problem/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_problem(problem_id):
    """問題編集"""
    try:
        if current_user.role not in ['admin', 'teacher']:
            flash('問題の編集権限がありません。')
            return redirect(url_for('problems.problems'))
        
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # 作成者または管理者のみ編集可能
        if current_user.role != 'admin' and problem.created_by != current_user.id:
            flash('この問題を編集する権限がありません。')
            return redirect(url_for('problems.problems'))
        
        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            options = request.form.get('options', '').strip()
            correct_answer = request.form.get('correct_answer', '').strip()
            explanation = request.form.get('explanation', '').strip()
            category_id = request.form.get('category_id', type=int)
            text_set_id = request.form.get('text_set_id', type=int)
            difficulty_level = request.form.get('difficulty_level', type=int)
            is_active = request.form.get('is_active') == 'on'
            
            # 入力値検証
            if not content:
                flash('問題文を入力してください。', 'error')
                return render_template('basebuilder/edit_problem.html',
                                     problem=problem,
                                     categories=ProblemCategory.query.all(),
                                     text_sets=TextSet.query.all())
            
            if not correct_answer:
                flash('正解を入力してください。', 'error')
                return render_template('basebuilder/edit_problem.html',
                                     problem=problem,
                                     categories=ProblemCategory.query.all(),
                                     text_sets=TextSet.query.all())
            
            # 選択肢のJSON変換
            options_list = []
            if options:
                try:
                    options_list = [opt.strip() for opt in options.split('\n') if opt.strip()]
                except:
                    flash('選択肢の形式が正しくありません。', 'error')
                    return render_template('basebuilder/edit_problem.html',
                                         problem=problem,
                                         categories=ProblemCategory.query.all(),
                                         text_sets=TextSet.query.all())
            
            # 問題情報を更新
            problem.content = content
            problem.options = json.dumps(options_list, ensure_ascii=False) if options_list else None
            problem.correct_answer = correct_answer
            problem.explanation = explanation
            problem.category_id = category_id
            problem.text_set_id = text_set_id if text_set_id else None
            problem.difficulty = difficulty_level or 1
            problem.is_active = is_active
            problem.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                
                current_app.logger.info(f"Problem {problem_id} updated by user {current_user.id}")
                flash('問題を更新しました。', 'success')
                return redirect(url_for('problems.problems'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Problem update error: {str(e)}")
                flash('問題の更新に失敗しました。', 'error')
        
        # GET リクエストの場合
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        text_sets = TextSet.query.order_by(TextSet.title).all()
        
        # 既存の選択肢をテキスト形式に変換
        existing_options = ""
        if problem.options:
            try:
                options_list = json.loads(problem.options)
                existing_options = '\n'.join(options_list)
            except:
                existing_options = ""
        
        return render_template('basebuilder/edit_problem.html',
                             problem=problem,
                             existing_options=existing_options,
                             categories=categories,
                             text_sets=text_sets)
        
    except Exception as e:
        current_app.logger.error(f"Edit problem error: {str(e)}")
        flash('問題編集画面の読み込み中にエラーが発生しました。')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/problem/<int:problem_id>/delete', methods=['POST'])
@login_required
def delete_problem(problem_id):
    """問題削除"""
    try:
        if current_user.role not in ['admin', 'teacher']:
            flash('問題の削除権限がありません。')
            return redirect(url_for('problems.problems'))
        
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # 作成者または管理者のみ削除可能
        if current_user.role != 'admin' and problem.created_by != current_user.id:
            flash('この問題を削除する権限がありません。')
            return redirect(url_for('problems.problems'))
        
        # 問題を削除
        db.session.delete(problem)
        db.session.commit()
        
        current_app.logger.info(f"Problem {problem_id} deleted by user {current_user.id}")
        flash('問題を削除しました。', 'success')
        return redirect(url_for('problems.problems'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Problem deletion error: {str(e)}")
        flash('問題の削除に失敗しました。', 'error')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/start_search_session')
@login_required
def start_search_session():
    """問題検索セッション開始"""
    try:
        if current_user.role != 'student':
            flash('学生のみアクセス可能です。')
            return redirect(url_for('problems.problems'))
        
        # セッションに問題検索モードを設定
        session['search_mode'] = True
        session['search_start_time'] = datetime.now().isoformat()
        
        flash('問題検索モードを開始しました。問題を選択して学習を始めてください。', 'info')
        return redirect(url_for('problems.problems'))
        
    except Exception as e:
        current_app.logger.error(f"Start search session error: {str(e)}")
        flash('検索セッションの開始中にエラーが発生しました。')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/api/problem/<int:problem_id>/details')
@login_required
def get_problem_details(problem_id):
    """問題詳細取得API"""
    try:
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # 基本情報
        problem_data = {
            'id': problem.id,
            'content': problem.content,
            'difficulty': problem.difficulty,
            'explanation': problem.explanation,
            'category': problem.category.name if problem.category else None,
            'text_set': problem.text_set.title if problem.text_set else None
        }
        
        # 選択肢がある場合
        if problem.options:
            try:
                problem_data['options'] = json.loads(problem.options)
            except:
                problem_data['options'] = []
        
        # 学生の場合、自分の回答履歴も含める
        if current_user.role == 'student':
            answer_records = AnswerRecord.query.filter_by(
                student_id=current_user.id,
                problem_id=problem_id
            ).order_by(AnswerRecord.created_at.desc()).limit(5).all()
            
            problem_data['recent_answers'] = [{
                'is_correct': record.is_correct,
                'response_time': record.response_time,
                'created_at': record.created_at.isoformat()
            } for record in answer_records]
        
        return jsonify({
            'success': True,
            'problem': problem_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Problem details API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': '問題詳細の取得に失敗しました'
        }), 500


@problems_bp.route('/download_problem_template/<template_type>')
@login_required
def download_problem_template(template_type):
    """問題テンプレートCSVのダウンロード"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        # CSVデータを作成
        output = StringIO()
        writer = csv.writer(output)
        
        # ヘッダー行
        headers = ['問題文', '選択肢1', '選択肢2', '選択肢3', '選択肢4', '正解番号', '難易度']
        writer.writerow(headers)
        
        # サンプルデータ（template_type == 'example'の場合）
        if template_type == 'example':
            sample_rows = [
                ['次のうち、日本の首都はどれですか？', '大阪', '京都', '東京', '名古屋', '3', '1'],
                ['2 + 2 = ?', '3', '4', '5', '6', '2', '1'],
                ['英語で「こんにちは」は？', 'Goodbye', 'Hello', 'Thank you', 'Sorry', '2', '1'],
            ]
            writer.writerows(sample_rows)
        
        # レスポンスの作成
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=problem_template_{template_type}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig'  # Excel対応のBOM付きUTF-8
            }
        )
        
        # BOMを追加（Excelでの文字化け対策）
        response.data = '\ufeff' + response.data
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Download template error: {str(e)}")
        flash('テンプレートのダウンロードに失敗しました。', 'error')
        return redirect(url_for('problems.problems'))


@problems_bp.route('/import_problems', methods=['GET', 'POST'])
@login_required
@require_roles(['admin', 'teacher'])
def import_problems():
    """問題のCSVインポート"""
    try:
        if request.method == 'GET':
            # カテゴリ一覧を取得
            categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
            return render_template('basebuilder/import_problems.html',
                                 categories=categories)
        
        # POST処理
        category_id = request.form.get('category_id', type=int)
        if not category_id:
            flash('カテゴリを選択してください。', 'error')
            return redirect(url_for('problems.import_problems'))
        
        # ファイルチェック
        if 'csv_file' not in request.files:
            flash('CSVファイルを選択してください。', 'error')
            return redirect(url_for('problems.import_problems'))
        
        csv_file = request.files['csv_file']
        if csv_file.filename == '':
            flash('CSVファイルを選択してください。', 'error')
            return redirect(url_for('problems.import_problems'))
        
        # CSVファイルの読み込み
        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            flash('CSVファイルのエンコーディングエラー。UTF-8形式で保存してください。', 'error')
            return redirect(url_for('problems.import_problems'))
        
        # 既存のインポート関数の代わりに直接処理
        import csv
        from io import StringIO
        
        # CSVパース
        csv_reader = csv.reader(StringIO(csv_content))
        headers = next(csv_reader, None)
        
        if not headers:
            flash('CSVファイルが空です。', 'error')
            return redirect(url_for('problems.import_problems'))
        
        # 期待するヘッダー
        expected_headers = ['問題文', '選択肢1', '選択肢2', '選択肢3', '選択肢4', '正解番号', '難易度']
        if headers != expected_headers:
            flash(f'CSVファイルのヘッダーが正しくありません。期待: {expected_headers}', 'error')
            return redirect(url_for('problems.import_problems'))
        
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            if len(row) != 7:
                errors.append(f'行{row_num}: 列数が正しくありません（期待: 7, 実際: {len(row)}）')
                continue
            
            try:
                question, choice1, choice2, choice3, choice4, correct_answer, difficulty = row
                
                # 正解番号の検証
                correct_answer_num = int(correct_answer)
                if correct_answer_num not in [1, 2, 3, 4]:
                    errors.append(f'行{row_num}: 正解番号は1-4の値である必要があります')
                    continue
                
                # 難易度の検証
                difficulty_num = int(difficulty)
                if difficulty_num not in [1, 2, 3, 4, 5]:
                    errors.append(f'行{row_num}: 難易度は1-5の値である必要があります')
                    continue
                
                # 問題を作成
                problem = BasicKnowledgeItem(
                    question=question,
                    choice1=choice1,
                    choice2=choice2,
                    choice3=choice3,
                    choice4=choice4,
                    correct_answer=correct_answer_num,
                    difficulty=difficulty_num,
                    category_id=category_id,
                    created_by=current_user.id,
                    school_id=getattr(current_user, 'school_id', None),
                    is_active=True
                )
                
                db.session.add(problem)
                imported_count += 1
                
            except (ValueError, TypeError) as e:
                errors.append(f'行{row_num}: データ形式エラー - {str(e)}')
                continue
            except Exception as e:
                errors.append(f'行{row_num}: 予期しないエラー - {str(e)}')
                continue
        
        success = imported_count > 0
        
        if success:
            db.session.commit()
            log_activity("problems_imported", f"Imported {imported_count} problems to category {category_id}")
            if errors:
                flash(f'{imported_count}件の問題をインポートしました（{len(errors)}件のエラーをスキップ）。', 'warning')
                for error in errors[:5]:  # 最初の5つのエラーのみ表示
                    flash(error, 'error')
            else:
                flash(f'{imported_count}件の問題をインポートしました。', 'success')
            return redirect(url_for('categories.category_problems', category_id=category_id))
        else:
            db.session.rollback()
            flash('問題をインポートできませんでした。', 'error')
            for error in errors[:5]:  # 最初の5つのエラーのみ表示
                flash(error, 'error')
            return redirect(url_for('problems.import_problems'))
        
    except Exception as e:
        current_app.logger.error(f"Import problems error: {str(e)}")
        flash('問題のインポート中にエラーが発生しました。', 'error')
        return redirect(url_for('problems.problems'))