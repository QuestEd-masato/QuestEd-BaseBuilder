# app/student/modules/unit_learning.py
"""単元詳細学習機能"""

from datetime import datetime
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import desc, func

from app.models import (
    CurriculumUnit, 
    StudentUnitSelection, 
    UnitItemMapping,
    db
)
from app.models.unit_progress import UnitProgressRecord
from basebuilder.models import BasicKnowledgeItem

from ..utils import student_required

unit_learning_bp = Blueprint("student_unit_learning", __name__)


@unit_learning_bp.route("/learning/unit/<int:unit_id>")
@login_required
@student_required
def unit_detail(unit_id):
    """単元詳細学習画面"""
    try:
        # 単元情報を取得
        unit = CurriculumUnit.query.get_or_404(unit_id)
        
        # 学生の選択状況を確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()
        
        if not selection:
            flash("この単元を学習するには、まず選択してください。", "warning")
            return redirect(url_for("student_learning.learning_portal"))
        
        # 単元に紐付けられた問題を取得
        problems = unit.get_mapped_problems()
        
        # 各問題の学習進捗を取得
        progress_records = {}
        for problem in problems:
            record = UnitProgressRecord.query.filter_by(
                student_id=current_user.id,
                unit_id=unit_id,
                item_id=problem.id
            ).first()
            progress_records[problem.id] = record
        
        # 進捗統計を計算
        total_problems = len(problems)
        completed_problems = len([r for r in progress_records.values() if r and r.status == "completed"])
        in_progress_problems = len([r for r in progress_records.values() if r and r.status == "in_progress"])
        
        progress_percentage = (completed_problems / total_problems * 100) if total_problems > 0 else 0
        
        # 単元選択の進捗を更新
        selection.total_items = total_problems
        selection.completed_items = completed_problems
        selection.progress_percentage = progress_percentage
        selection.update_progress()
        db.session.commit()
        
        return render_template(
            "student/unit_detail.html",
            unit=unit,
            selection=selection,
            problems=problems,
            progress_records=progress_records,
            stats={
                "total_problems": total_problems,
                "completed_problems": completed_problems,
                "in_progress_problems": in_progress_problems,
                "progress_percentage": progress_percentage,
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Unit detail error: {str(e)}")
        flash("単元詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_learning.learning_portal"))


@unit_learning_bp.route("/learning/unit/<int:unit_id>/problem/<int:item_id>")
@login_required
@student_required  
def problem_detail(unit_id, item_id):
    """問題詳細学習画面"""
    try:
        # 単元と問題を取得
        unit = CurriculumUnit.query.get_or_404(unit_id)
        problem = BasicKnowledgeItem.query.get_or_404(item_id)
        
        # 単元選択確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()
        
        if not selection:
            flash("この単元を学習するには、まず選択してください。", "warning")
            return redirect(url_for("student_learning.learning_portal"))
        
        # 問題が単元に紐付いているか確認
        mapping = UnitItemMapping.query.filter_by(
            unit_id=unit_id, item_id=item_id
        ).first()
        
        if not mapping:
            flash("この問題は指定された単元に含まれていません。", "error")
            return redirect(url_for("student_unit_learning.unit_detail", unit_id=unit_id))
        
        # 学習進捗記録を取得または作成
        progress_record = UnitProgressRecord.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id,
            item_id=item_id
        ).first()
        
        if not progress_record:
            progress_record = UnitProgressRecord(
                student_id=current_user.id,
                unit_id=unit_id,
                item_id=item_id,
                status="not_started"
            )
            db.session.add(progress_record)
            db.session.commit()
        
        # 学習開始処理
        if progress_record.status == "not_started":
            progress_record.start_learning()
            db.session.commit()
        
        return render_template(
            "student/problem_learning.html",
            unit=unit,
            problem=problem,
            progress_record=progress_record,
            mapping=mapping,
        )
        
    except Exception as e:
        current_app.logger.error(f"Problem detail error: {str(e)}")
        flash("問題詳細の読み込み中にエラーが発生しました。", "error")
        return redirect(url_for("student_unit_learning.unit_detail", unit_id=unit_id))


@unit_learning_bp.route("/learning/unit/<int:unit_id>/problem/<int:item_id>/complete", methods=["POST"])
@login_required
@student_required
def complete_problem(unit_id, item_id):
    """問題完了処理"""
    try:
        data = request.get_json() or {}
        
        # 進捗記録を取得
        progress_record = UnitProgressRecord.query.filter_by(
            student_id=current_user.id,
            unit_id=unit_id,
            item_id=item_id
        ).first()
        
        if not progress_record:
            return jsonify({"success": False, "message": "進捗記録が見つかりません"}), 404
        
        # 完了処理
        self_rating = data.get("self_rating")
        difficulty_rating = data.get("difficulty_rating")
        notes = data.get("notes", "").strip()
        
        progress_record.complete_learning(
            self_rating=self_rating,
            difficulty_rating=difficulty_rating,
            notes=notes
        )
        progress_record.calculate_study_time()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "問題を完了しました",
            "study_time": progress_record.get_study_time_formatted()
        })
        
    except Exception as e:
        current_app.logger.error(f"Complete problem error: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "message": "完了処理中にエラーが発生しました"}), 500


@unit_learning_bp.route("/learning/unit/<int:unit_id>/request-completion", methods=["POST"])
@login_required
@student_required
def request_unit_completion(unit_id):
    """単元完了申請"""
    try:
        data = request.get_json() or {}
        
        # 単元選択を取得
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()
        
        if not selection:
            return jsonify({"success": False, "message": "単元が選択されていません"}), 400
        
        # 進捗率チェック
        if selection.progress_percentage < 80:
            return jsonify({
                "success": False, 
                "message": f"完了申請には80%以上の進捗が必要です（現在: {selection.progress_percentage:.1f}%）"
            }), 400
        
        # 完了申請処理
        completion_notes = data.get("completion_notes", "").strip()
        
        selection.request_completion(notes=completion_notes)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "単元完了申請を送信しました。教師の承認をお待ちください。"
        })
        
    except Exception as e:
        current_app.logger.error(f"Request unit completion error: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "message": "完了申請中にエラーが発生しました"}), 500


@unit_learning_bp.route("/learning/unit/<int:unit_id>/progress")
@login_required
@student_required
def get_unit_progress(unit_id):
    """単元進捗情報API"""
    try:
        # 単元選択を取得
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()
        
        if not selection:
            return jsonify({"success": False, "message": "単元が選択されていません"}), 404
        
        # 詳細進捗を取得
        progress_records = UnitProgressRecord.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).all()
        
        return jsonify({
            "success": True,
            "selection": selection.to_dict(),
            "progress_records": [record.to_dict() for record in progress_records]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get unit progress error: {str(e)}")
        return jsonify({"success": False, "message": "進捗取得中にエラーが発生しました"}), 500


@unit_learning_bp.route("/api/units/<int:unit_id>/curriculum")
@login_required
@student_required
def get_unit_curriculum(unit_id):
    """単元カリキュラム詳細API"""
    try:
        # 単元情報を取得
        unit = CurriculumUnit.query.get_or_404(unit_id)
        
        # 単元に紐付けられた問題を取得
        problems = unit.get_mapped_problems()
        
        # 各問題の学習進捗を取得
        progress_records = {}
        for problem in problems:
            record = UnitProgressRecord.query.filter_by(
                student_id=current_user.id,
                unit_id=unit_id,
                item_id=problem.id
            ).first()
            progress_records[problem.id] = record
        
        # カリキュラム詳細を構築
        curriculum_data = {
            "unit": {
                "id": unit.id,
                "title": unit.title,
                "description": unit.description,
                "difficulty_level": unit.difficulty_level,
                "estimated_minutes": unit.estimated_minutes
            },
            "problems": [
                {
                    "id": problem.id,
                    "title": problem.title,
                    "question": problem.question,
                    "status": progress_records.get(problem.id).status if progress_records.get(problem.id) else "not_started"
                }
                for problem in problems
            ],
            "total_problems": len(problems),
            "learning_objectives": {
                "completion_criteria": "80%以上の問題を完了すること",
                "understanding_goal": "各問題で3段階以上の自己評価",
                "time_estimate": f"{unit.estimated_minutes}分程度",
                "approval_process": "問題完了 → 進捗確認 → 教師承認申請"
            }
        }
        
        return jsonify({
            "success": True,
            "data": curriculum_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get unit curriculum error: {str(e)}")
        return jsonify({"success": False, "message": "カリキュラム取得中にエラーが発生しました"}), 500


@unit_learning_bp.route("/api/units/<int:unit_id>/award-completion-points", methods=["POST"])
@login_required
@student_required  
def award_completion_points(unit_id):
    """単元完了時のランキングポイント加算（教師承認後に呼び出される）"""
    try:
        from basebuilder.models import WordProficiency
        
        # 単元選択確認
        selection = StudentUnitSelection.query.filter_by(
            student_id=current_user.id, unit_id=unit_id
        ).first()
        
        if not selection or selection.approval_status != 'approved':
            return jsonify({"success": False, "message": "承認済みの単元ではありません"}), 400
            
        # 既にポイント加算済みかチェック
        if hasattr(selection, 'points_awarded') and selection.points_awarded:
            return jsonify({"success": False, "message": "既にポイントが加算されています"}), 400
        
        # WordProficiencyテーブルに100ポイント相当の記録を追加
        # （実際のランキングシステムと連携するまでの代替手段）
        unit = CurriculumUnit.query.get(unit_id)
        if not unit:
            return jsonify({"success": False, "message": "単元が見つかりません"}), 404
            
        # 単元完了として仮想的なWordProficiency記録を作成（ランキング用）
        completion_bonus = WordProficiency(
            student_id=current_user.id,
            word_id=99999 + unit_id,  # 仮想的なword_id（単元完了ボーナス用）
            level=5,  # 最高レベル
            review_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(completion_bonus)
        
        # 単元選択にポイント加算フラグを設定（カラムが存在する場合）
        try:
            selection.points_awarded = True
            selection.points_awarded_at = datetime.utcnow()
        except AttributeError:
            # カラムが存在しない場合は完了メモに記録
            if selection.completion_notes:
                selection.completion_notes += f"\n[システム] ランキングポイント100pt加算済み ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"
            else:
                selection.completion_notes = f"[システム] ランキングポイント100pt加算済み ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"
        
        db.session.commit()
        
        current_app.logger.info(
            f"[UNIT_COMPLETION] Student {current_user.id} awarded 100 points for completing unit {unit_id}"
        )
        
        return jsonify({
            "success": True,
            "message": "単元完了により100ポイントが加算されました！",
            "points_awarded": 100
        })
        
    except Exception as e:
        current_app.logger.error(f"Award completion points error: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "message": "ポイント加算中にエラーが発生しました"}), 500