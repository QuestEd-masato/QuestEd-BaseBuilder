# -*- coding: utf-8 -*-
"""
TeacherStatisticsService

教師用統計・分析専門サービス
UnitSelectionManagerの統計ロジックを抽出・統合
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumUnit, StudentUnitSelection, ClassEnrollment, db
)

logger = logging.getLogger(__name__)


class TeacherStatisticsService:
    """教師統計専門サービス"""

    def get_unit_statistics(self, unit_id: int) -> Dict[str, Any]:
        """
        単元統計情報を取得
        
        Args:
            unit_id: 単元ID
            
        Returns:
            Dict: 統計情報
        """
        try:
            logger.info(f"Getting unit statistics for unit {unit_id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "統計閲覧権限がありません"
                }

            # 単元の存在確認
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "指定された単元が見つかりません"
                }

            # 基本統計の計算
            basic_stats = self._calculate_basic_unit_stats(unit_id)
            
            # 進捗分布の計算
            progress_distribution = self._calculate_progress_distribution(unit_id)
            
            # 学習時間統計の計算
            time_stats = self._calculate_study_time_stats(unit_id)
            
            # トレンド分析の計算
            trend_data = self._calculate_unit_trends(unit_id)
            
            return {
                "success": True,
                "unit_id": unit_id,
                "unit_title": unit.title,
                "basic_statistics": basic_stats,
                "progress_distribution": progress_distribution,
                "time_statistics": time_stats,
                "trend_analysis": trend_data,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting unit statistics: {str(e)}")
            return {
                "success": False,
                "message": f"統計情報の取得中にエラーが発生しました: {str(e)}"
            }

    def get_teacher_overview_statistics(self, teacher_id: Optional[int] = None) -> Dict[str, Any]:
        """
        教師の全体統計概要を取得
        
        Args:
            teacher_id: 教師ID（指定されない場合は現在のユーザー）
            
        Returns:
            Dict: 全体統計概要
        """
        try:
            target_teacher_id = teacher_id or current_user.id
            logger.info(f"Getting teacher overview statistics for teacher {target_teacher_id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "統計閲覧権限がありません"
                }

            # 教師が担当する単元の取得
            teacher_units = self._get_teacher_units(target_teacher_id)
            
            # 全体統計の計算
            overall_stats = self._calculate_teacher_overall_stats(teacher_units)
            
            # クラス別統計の計算
            class_stats = self._calculate_class_statistics(target_teacher_id)
            
            # 最近の活動統計
            recent_activity = self._calculate_recent_activity(teacher_units)
            
            return {
                "success": True,
                "teacher_id": target_teacher_id,
                "overall_statistics": overall_stats,
                "class_statistics": class_stats,
                "recent_activity": recent_activity,
                "total_units": len(teacher_units),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting teacher overview statistics: {str(e)}")
            return {
                "success": False,
                "message": f"教師統計の取得中にエラーが発生しました: {str(e)}"
            }

    def get_class_progress_summary(self, class_id: int) -> Dict[str, Any]:
        """
        クラス進捗サマリーを取得
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: クラス進捗サマリー
        """
        try:
            logger.info(f"Getting class progress summary for class {class_id}")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "クラス統計閲覧権限がありません"
                }

            # クラスの学生一覧取得
            students = self._get_class_students(class_id)
            
            # 学生別進捗の計算
            student_progress = self._calculate_student_progress(students)
            
            # クラス全体の統計
            class_summary = self._calculate_class_summary(students)
            
            return {
                "success": True,
                "class_id": class_id,
                "student_progress": student_progress,
                "class_summary": class_summary,
                "total_students": len(students),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting class progress summary: {str(e)}")
            return {
                "success": False,
                "message": f"クラス進捗サマリーの取得中にエラーが発生しました: {str(e)}"
            }

    def get_performance_analytics(self, unit_id: Optional[int] = None, 
                                 days_back: int = 30) -> Dict[str, Any]:
        """
        パフォーマンス分析データを取得
        
        Args:
            unit_id: 単元ID（指定時は該当単元のみ）
            days_back: 過去何日分のデータを分析するか
            
        Returns:
            Dict: パフォーマンス分析データ
        """
        try:
            logger.info(f"Getting performance analytics for unit {unit_id}, {days_back} days back")
            
            # 権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "分析データ閲覧権限がありません"
                }

            # 分析期間の設定
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # パフォーマンス指標の計算
            performance_metrics = self._calculate_performance_metrics(unit_id, start_date, end_date)
            
            # 学習パターン分析
            learning_patterns = self._analyze_learning_patterns(unit_id, start_date, end_date)
            
            # 問題識別
            identified_issues = self._identify_performance_issues(unit_id, start_date, end_date)
            
            return {
                "success": True,
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days_analyzed": days_back
                },
                "performance_metrics": performance_metrics,
                "learning_patterns": learning_patterns,
                "identified_issues": identified_issues,
                "unit_id": unit_id,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting performance analytics: {str(e)}")
            return {
                "success": False,
                "message": f"パフォーマンス分析中にエラーが発生しました: {str(e)}"
            }

    def _calculate_basic_unit_stats(self, unit_id: int) -> Dict[str, Any]:
        """基本的な単元統計の計算"""
        selections = StudentUnitSelection.query.filter_by(unit_id=unit_id).all()
        
        total_selections = len(selections)
        completed_count = len([s for s in selections if s.status == 'completed'])
        in_progress_count = len([s for s in selections if s.status == 'in_progress'])
        
        completion_rate = (completed_count / total_selections * 100) if total_selections > 0 else 0
        
        # 平均進捗率の計算
        progress_values = [s.progress_percentage for s in selections if s.progress_percentage is not None]
        average_progress = sum(progress_values) / len(progress_values) if progress_values else 0
        
        return {
            "total_selections": total_selections,
            "completed_count": completed_count,
            "in_progress_count": in_progress_count,
            "not_started_count": total_selections - completed_count - in_progress_count,
            "completion_rate": round(completion_rate, 2),
            "average_progress": round(average_progress, 2)
        }

    def _calculate_progress_distribution(self, unit_id: int) -> Dict[str, Any]:
        """進捗分布の計算"""
        selections = StudentUnitSelection.query.filter_by(unit_id=unit_id).all()
        
        distribution_ranges = {
            "0-20": 0,
            "21-40": 0,
            "41-60": 0,
            "61-80": 0,
            "81-100": 0
        }
        
        for selection in selections:
            progress = selection.progress_percentage or 0
            if progress <= 20:
                distribution_ranges["0-20"] += 1
            elif progress <= 40:
                distribution_ranges["21-40"] += 1
            elif progress <= 60:
                distribution_ranges["41-60"] += 1
            elif progress <= 80:
                distribution_ranges["61-80"] += 1
            else:
                distribution_ranges["81-100"] += 1
        
        return distribution_ranges

    def _calculate_study_time_stats(self, unit_id: int) -> Dict[str, Any]:
        """学習時間統計の計算"""
        selections = StudentUnitSelection.query.filter_by(unit_id=unit_id).all()
        
        study_times = [s.study_time_minutes for s in selections if s.study_time_minutes is not None]
        
        if not study_times:
            return {
                "total_study_time": 0,
                "average_study_time": 0,
                "median_study_time": 0,
                "min_study_time": 0,
                "max_study_time": 0
            }
        
        study_times.sort()
        median_index = len(study_times) // 2
        
        return {
            "total_study_time": sum(study_times),
            "average_study_time": round(sum(study_times) / len(study_times), 2),
            "median_study_time": study_times[median_index],
            "min_study_time": min(study_times),
            "max_study_time": max(study_times)
        }

    def _calculate_unit_trends(self, unit_id: int) -> Dict[str, Any]:
        """単元のトレンド分析"""
        # 過去30日間の選択・完了データを取得
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_selections = StudentUnitSelection.query.filter(
            StudentUnitSelection.unit_id == unit_id,
            StudentUnitSelection.selected_at >= thirty_days_ago
        ).all()
        
        recent_completions = StudentUnitSelection.query.filter(
            StudentUnitSelection.unit_id == unit_id,
            StudentUnitSelection.completed_at >= thirty_days_ago
        ).all()
        
        return {
            "recent_selections": len(recent_selections),
            "recent_completions": len(recent_completions),
            "selection_trend": "increasing" if len(recent_selections) > 5 else "stable",
            "completion_trend": "increasing" if len(recent_completions) > 3 else "stable"
        }

    def _get_teacher_units(self, teacher_id: int) -> List[CurriculumUnit]:
        """教師が担当する単元一覧を取得"""
        # 実際の実装では、教師と単元の関連を適切に取得
        # ここでは簡略化して全単元を返す
        return CurriculumUnit.query.filter_by(is_active=True).all()

    def _calculate_teacher_overall_stats(self, units: List[CurriculumUnit]) -> Dict[str, Any]:
        """教師の全体統計計算"""
        unit_ids = [unit.id for unit in units]
        
        total_selections = StudentUnitSelection.query.filter(
            StudentUnitSelection.unit_id.in_(unit_ids)
        ).count()
        
        completed_selections = StudentUnitSelection.query.filter(
            StudentUnitSelection.unit_id.in_(unit_ids),
            StudentUnitSelection.status == 'completed'
        ).count()
        
        overall_completion_rate = (completed_selections / total_selections * 100) if total_selections > 0 else 0
        
        return {
            "total_units": len(units),
            "total_student_selections": total_selections,
            "total_completions": completed_selections,
            "overall_completion_rate": round(overall_completion_rate, 2)
        }

    def _calculate_class_statistics(self, teacher_id: int) -> List[Dict[str, Any]]:
        """クラス別統計の計算"""
        # 簡略化した実装
        return []

    def _calculate_recent_activity(self, units: List[CurriculumUnit]) -> Dict[str, Any]:
        """最近の活動統計"""
        unit_ids = [unit.id for unit in units]
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_activity = StudentUnitSelection.query.filter(
            StudentUnitSelection.unit_id.in_(unit_ids),
            StudentUnitSelection.last_accessed >= seven_days_ago
        ).count()
        
        return {
            "active_students_last_7_days": recent_activity,
            "trend": "stable"
        }

    def _get_class_students(self, class_id: int) -> List[Dict[str, Any]]:
        """クラスの学生一覧取得"""
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        return [{"id": e.student_id, "enrollment": e} for e in enrollments]

    def _calculate_student_progress(self, students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """学生別進捗計算"""
        progress_data = []
        
        for student in students:
            student_selections = StudentUnitSelection.query.filter_by(
                student_id=student["id"]
            ).all()
            
            completed_count = len([s for s in student_selections if s.status == 'completed'])
            total_count = len(student_selections)
            
            progress_data.append({
                "student_id": student["id"],
                "total_selections": total_count,
                "completed_selections": completed_count,
                "completion_rate": (completed_count / total_count * 100) if total_count > 0 else 0
            })
        
        return progress_data

    def _calculate_class_summary(self, students: List[Dict[str, Any]]) -> Dict[str, Any]:
        """クラス全体サマリー計算"""
        total_students = len(students)
        
        if total_students == 0:
            return {
                "total_students": 0,
                "average_completion_rate": 0,
                "active_students": 0
            }
        
        # 簡略化した計算
        return {
            "total_students": total_students,
            "average_completion_rate": 0,
            "active_students": 0
        }

    def _calculate_performance_metrics(self, unit_id: Optional[int], 
                                     start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """パフォーマンス指標計算"""
        return {
            "completion_velocity": 0,
            "engagement_score": 0,
            "difficulty_index": 0
        }

    def _analyze_learning_patterns(self, unit_id: Optional[int], 
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """学習パターン分析"""
        return {
            "peak_learning_hours": [],
            "common_sticking_points": [],
            "optimal_study_duration": 0
        }

    def _identify_performance_issues(self, unit_id: Optional[int], 
                                   start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """パフォーマンス問題の識別"""
        return []