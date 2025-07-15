# app/student/modules/surveys.py
"""学生アンケート機能"""

import json
import logging
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.models import InterestSurvey, PersonalitySurvey, db

from ..utils import get_student_survey_status, student_required

surveys_bp = Blueprint("student_surveys", __name__)


@surveys_bp.route("/surveys")
@login_required
@student_required
def surveys():
    """アンケート一覧"""
    try:
        # アンケート完了状況を取得
        survey_status = get_student_survey_status()

        # 既存のアンケートデータを取得
        interest_survey = InterestSurvey.query.filter_by(
            student_id=current_user.id
        ).first()
        personality_survey = PersonalitySurvey.query.filter_by(
            student_id=current_user.id
        ).first()

        return render_template(
            "surveys.html",
            survey_status=survey_status,
            interest_survey=interest_survey,
            personality_survey=personality_survey,
        )

    except Exception as e:
        current_app.logger.error(f"Surveys list error: {str(e)}")
        flash("アンケート一覧の読み込み中にエラーが発生しました。")
        return redirect(url_for("student_dashboard.dashboard"))


@surveys_bp.route("/interest_survey", methods=["GET", "POST"])
@login_required
@student_required
def interest_survey():
    """興味関心アンケート"""
    try:
        # 既存のアンケートデータを取得
        existing_survey = InterestSurvey.query.filter_by(
            student_id=current_user.id
        ).first()

        if request.method == "POST":
            # フォームデータを収集
            survey_data = {}

            # 興味分野（複数選択可）
            interests = request.form.getlist("interests")
            survey_data["interests"] = interests

            # 好きな教科（複数選択可）
            subjects = request.form.getlist("subjects")
            survey_data["subjects"] = subjects

            # 趣味・特技
            hobbies = request.form.get("hobbies", "").strip()
            survey_data["hobbies"] = hobbies

            # 将来の夢・目標
            future_goals = request.form.get("future_goals", "").strip()
            survey_data["future_goals"] = future_goals

            # 学習スタイル
            learning_style = request.form.get("learning_style")
            survey_data["learning_style"] = learning_style

            # 好きな学習方法（複数選択可）
            learning_methods = request.form.getlist("learning_methods")
            survey_data["learning_methods"] = learning_methods

            # 興味のある職業
            career_interests = request.form.getlist("career_interests")
            survey_data["career_interests"] = career_interests

            # 特記事項
            notes = request.form.get("notes", "").strip()
            survey_data["notes"] = notes

            try:
                if existing_survey:
                    # 既存のアンケートを更新
                    existing_survey.interests = json.dumps(
                        survey_data, ensure_ascii=False
                    )
                    existing_survey.updated_at = datetime.utcnow()
                    flash("興味関心アンケートを更新しました。", "success")
                else:
                    # 新規アンケートを作成
                    new_survey = InterestSurvey(
                        student_id=current_user.id,
                        interests=json.dumps(survey_data, ensure_ascii=False),
                    )
                    db.session.add(new_survey)
                    flash("興味関心アンケートを提出しました。", "success")

                db.session.commit()
                return redirect(url_for("student_surveys.surveys"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Interest survey save error: {str(e)}")
                flash("アンケートの保存に失敗しました。", "error")

        # 既存データをパース（編集時）
        existing_data = {}
        if existing_survey and existing_survey.interests:
            try:
                existing_data = json.loads(existing_survey.interests)
            except json.JSONDecodeError:
                current_app.logger.warning(
                    f"Invalid JSON in interest survey {existing_survey.id}"
                )

        return render_template(
            "interest_survey.html",
            existing_data=existing_data,
            is_editing=existing_survey is not None,
        )

    except Exception as e:
        current_app.logger.error(f"Interest survey error: {str(e)}")
        flash("興味関心アンケートの読み込み中にエラーが発生しました。")
        return redirect(url_for("student_surveys.surveys"))


@surveys_bp.route("/interest_survey/edit")
@login_required
@student_required
def interest_survey_edit():
    """興味関心アンケート編集（リダイレクト）"""
    return redirect(url_for("student_surveys.interest_survey"))


@surveys_bp.route("/personality_survey", methods=["GET", "POST"])
@login_required
@student_required
def personality_survey():
    """性格・特性アンケート"""
    try:
        # 既存のアンケートデータを取得
        existing_survey = PersonalitySurvey.query.filter_by(
            student_id=current_user.id
        ).first()

        if request.method == "POST":
            # フォームデータを収集
            survey_data = {}

            # 性格特性（5点尺度）
            personality_traits = [
                "extroversion",  # 外向性
                "agreeableness",  # 協調性
                "conscientiousness",  # 誠実性
                "neuroticism",  # 神経症的傾向
                "openness",  # 開放性
            ]

            for trait in personality_traits:
                value = request.form.get(trait, type=int)
                if value and 1 <= value <= 5:
                    survey_data[trait] = value

            # 学習傾向
            learning_preferences = request.form.getlist("learning_preferences")
            survey_data["learning_preferences"] = learning_preferences

            # コミュニケーションスタイル
            communication_style = request.form.get("communication_style")
            survey_data["communication_style"] = communication_style

            # 困難への対処法
            problem_solving = request.form.get("problem_solving")
            survey_data["problem_solving"] = problem_solving

            # モチベーションの源泉
            motivation_sources = request.form.getlist("motivation_sources")
            survey_data["motivation_sources"] = motivation_sources

            # ストレス対処法
            stress_management = request.form.getlist("stress_management")
            survey_data["stress_management"] = stress_management

            # 自己評価コメント
            self_evaluation = request.form.get("self_evaluation", "").strip()
            survey_data["self_evaluation"] = self_evaluation

            # 入力値検証
            if not any(trait in survey_data for trait in personality_traits):
                flash("性格特性の評価を入力してください。", "error")
                return render_template(
                    "personality_survey.html",
                    existing_data=survey_data,
                    is_editing=existing_survey is not None,
                )

            try:
                if existing_survey:
                    # 既存のアンケートを更新
                    existing_survey.personality = json.dumps(
                        survey_data, ensure_ascii=False
                    )
                    existing_survey.updated_at = datetime.utcnow()
                    flash("性格・特性アンケートを更新しました。", "success")
                else:
                    # 新規アンケートを作成
                    new_survey = PersonalitySurvey(
                        student_id=current_user.id,
                        personality=json.dumps(survey_data, ensure_ascii=False),
                    )
                    db.session.add(new_survey)
                    flash("性格・特性アンケートを提出しました。", "success")

                db.session.commit()
                return redirect(url_for("student_surveys.surveys"))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Personality survey save error: {str(e)}")
                flash("アンケートの保存に失敗しました。", "error")

        # 既存データをパース（編集時）
        existing_data = {}
        if existing_survey and existing_survey.personality:
            try:
                existing_data = json.loads(existing_survey.personality)
            except json.JSONDecodeError:
                current_app.logger.warning(
                    f"Invalid JSON in personality survey {existing_survey.id}"
                )

        return render_template(
            "personality_survey.html",
            existing_data=existing_data,
            is_editing=existing_survey is not None,
        )

    except Exception as e:
        current_app.logger.error(f"Personality survey error: {str(e)}")
        flash("性格・特性アンケートの読み込み中にエラーが発生しました。")
        return redirect(url_for("student_surveys.surveys"))


@surveys_bp.route("/personality_survey/edit")
@login_required
@student_required
def personality_survey_edit():
    """性格・特性アンケート編集（リダイレクト）"""
    return redirect(url_for("student_surveys.personality_survey"))


@surveys_bp.route("/api/survey-status")
@login_required
@student_required
def api_survey_status():
    """アンケート完了状況API"""
    try:
        survey_status = get_student_survey_status()

        # 詳細情報を追加
        interest_survey = InterestSurvey.query.filter_by(
            student_id=current_user.id
        ).first()
        personality_survey = PersonalitySurvey.query.filter_by(
            student_id=current_user.id
        ).first()

        detailed_status = {
            "interest_completed": survey_status["interest_completed"],
            "personality_completed": survey_status["personality_completed"],
            "all_completed": survey_status["all_completed"],
            "interest_updated_at": interest_survey.updated_at.isoformat()
            if interest_survey and interest_survey.updated_at
            else None,
            "personality_updated_at": personality_survey.updated_at.isoformat()
            if personality_survey and personality_survey.updated_at
            else None,
            "can_generate_themes": survey_status["all_completed"],
        }

        return {"success": True, "status": detailed_status}

    except Exception as e:
        return {"success": False, "error": str(e)}, 500


@surveys_bp.route("/survey-summary")
@login_required
@student_required
def survey_summary():
    """アンケート結果サマリー表示"""
    try:
        # アンケート完了状況を確認
        survey_status = get_student_survey_status()

        if not survey_status["all_completed"]:
            flash("すべてのアンケートを完了してから確認してください。")
            return redirect(url_for("student_surveys.surveys"))

        # アンケートデータを取得
        interest_survey = InterestSurvey.query.filter_by(
            student_id=current_user.id
        ).first()
        personality_survey = PersonalitySurvey.query.filter_by(
            student_id=current_user.id
        ).first()

        # データをパース
        interest_data = {}
        personality_data = {}

        if interest_survey and interest_survey.interests:
            try:
                interest_data = json.loads(interest_survey.interests)
            except json.JSONDecodeError:
                pass

        if personality_survey and personality_survey.personality:
            try:
                personality_data = json.loads(personality_survey.personality)
            except json.JSONDecodeError:
                pass

        return render_template(
            "survey_summary.html",
            interest_data=interest_data,
            personality_data=personality_data,
        )

    except Exception as e:
        current_app.logger.error(f"Survey summary error: {str(e)}")
        flash("アンケート結果の表示中にエラーが発生しました。")
        return redirect(url_for("student_surveys.surveys"))
