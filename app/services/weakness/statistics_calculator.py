"""
Weakness Statistics Calculator
==============================
統計計算専門モジュール

責任:
- 学習データの統計的分析
- 平均値、分散、標準偏差の計算
- パフォーマンス指標の算出
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class WeaknessStatisticsCalculator:
    """統計計算クラス"""

    def calculate_statistics(self, learning_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        学習データから各種統計を計算

        Args:
            learning_data: 収集された学習データ

        Returns:
            dict: 計算された統計情報
        """
        try:
            stats = {
                "calculation_date": datetime.now(),
                "answer_statistics": self._calculate_answer_statistics(
                    learning_data.get("answer_records", [])
                ),
                "category_statistics": self._calculate_category_statistics(
                    learning_data.get("answer_records", [])
                ),
                "time_statistics": self._calculate_time_statistics(
                    learning_data.get("answer_records", [])
                ),
                "difficulty_statistics": self._calculate_difficulty_statistics(
                    learning_data.get("answer_records", [])
                ),
                "unit_statistics": self._calculate_unit_statistics(
                    learning_data.get("unit_progress", [])
                ),
                "activity_statistics": self._calculate_activity_statistics(
                    learning_data.get("activity_logs", [])
                ),
                "basebuilder_statistics": self._calculate_basebuilder_statistics(
                    learning_data.get("basebuilder_data", {})
                ),
            }

            current_app.logger.info(
                f"Calculated statistics for student {learning_data.get('student_id')}"
            )

            return stats

        except Exception as e:
            current_app.logger.error(f"Error calculating statistics: {str(e)}")
            return self._get_empty_statistics()

    def _calculate_answer_statistics(self, answer_records: List[Dict]) -> Dict:
        """回答統計を計算"""
        if not answer_records:
            return {
                "total_answers": 0,
                "correct_answers": 0,
                "accuracy_rate": 0.0,
                "avg_response_time": 0.0,
            }

        correct_count = sum(1 for r in answer_records if r["is_correct"])
        response_times = [
            r["response_time"] for r in answer_records if r.get("response_time")
        ]

        return {
            "total_answers": len(answer_records),
            "correct_answers": correct_count,
            "accuracy_rate": correct_count / len(answer_records)
            if answer_records
            else 0,
            "avg_response_time": statistics.mean(response_times)
            if response_times
            else 0,
            "median_response_time": statistics.median(response_times)
            if response_times
            else 0,
            "response_time_std": statistics.stdev(response_times)
            if len(response_times) > 1
            else 0,
        }

    def _calculate_category_statistics(self, answer_records: List[Dict]) -> Dict:
        """カテゴリ別統計を計算"""
        category_data = defaultdict(lambda: {"total": 0, "correct": 0})

        for record in answer_records:
            if record.get("problem") and record["problem"].get("category_id"):
                category_id = record["problem"]["category_id"]
                category_data[category_id]["total"] += 1
                if record["is_correct"]:
                    category_data[category_id]["correct"] += 1

        category_stats = {}
        for cat_id, data in category_data.items():
            accuracy = data["correct"] / data["total"] if data["total"] > 0 else 0
            category_stats[cat_id] = {
                "total_attempts": data["total"],
                "correct_answers": data["correct"],
                "accuracy_rate": accuracy,
                "performance_level": self._get_performance_level(accuracy),
            }

        return category_stats

    def _calculate_time_statistics(self, answer_records: List[Dict]) -> Dict:
        """時間帯別統計を計算"""
        hourly_performance = defaultdict(lambda: {"total": 0, "correct": 0})
        daily_performance = defaultdict(lambda: {"total": 0, "correct": 0})

        for record in answer_records:
            if record.get("created_at"):
                hour = record["created_at"].hour
                day = record["created_at"].weekday()

                hourly_performance[hour]["total"] += 1
                daily_performance[day]["total"] += 1

                if record["is_correct"]:
                    hourly_performance[hour]["correct"] += 1
                    daily_performance[day]["correct"] += 1

        # 最も効果的な時間帯を特定
        best_hour = None
        best_hour_accuracy = 0

        for hour, data in hourly_performance.items():
            if data["total"] >= 5:  # 最低5回の試行がある時間帯のみ
                accuracy = data["correct"] / data["total"]
                if accuracy > best_hour_accuracy:
                    best_hour = hour
                    best_hour_accuracy = accuracy

        return {
            "hourly_performance": dict(hourly_performance),
            "daily_performance": dict(daily_performance),
            "best_performance_hour": best_hour,
            "best_hour_accuracy": best_hour_accuracy,
        }

    def _calculate_difficulty_statistics(self, answer_records: List[Dict]) -> Dict:
        """難易度別統計を計算"""
        difficulty_data = defaultdict(lambda: {"total": 0, "correct": 0})

        for record in answer_records:
            if record.get("problem") and record["problem"].get("difficulty_level"):
                level = record["problem"]["difficulty_level"]
                difficulty_data[level]["total"] += 1
                if record["is_correct"]:
                    difficulty_data[level]["correct"] += 1

        difficulty_stats = {}
        for level, data in difficulty_data.items():
            accuracy = data["correct"] / data["total"] if data["total"] > 0 else 0
            difficulty_stats[level] = {
                "total_attempts": data["total"],
                "correct_answers": data["correct"],
                "accuracy_rate": accuracy,
                "mastery_status": self._get_mastery_status(accuracy, level),
            }

        return difficulty_stats

    def _calculate_unit_statistics(self, unit_progress: List[Dict]) -> Dict:
        """単元統計を計算"""
        total_units = len(unit_progress)
        completed_units = sum(1 for u in unit_progress if u["status"] == "completed")
        in_progress_units = sum(
            1 for u in unit_progress if u["status"] == "in_progress"
        )

        progress_values = [
            u["progress_percentage"] for u in unit_progress if u["progress_percentage"]
        ]

        return {
            "total_units": total_units,
            "completed_units": completed_units,
            "in_progress_units": in_progress_units,
            "not_started_units": total_units - completed_units - in_progress_units,
            "completion_rate": completed_units / total_units if total_units > 0 else 0,
            "avg_progress": statistics.mean(progress_values) if progress_values else 0,
            "median_progress": statistics.median(progress_values)
            if progress_values
            else 0,
        }

    def _calculate_activity_statistics(self, activity_logs: List[Dict]) -> Dict:
        """活動統計を計算"""
        if not activity_logs:
            return {
                "total_activities": 0,
                "avg_activities_per_day": 0,
                "activity_streak": 0,
            }

        # 日付別活動数を計算
        daily_activities = defaultdict(int)
        for log in activity_logs:
            if log.get("created_at"):
                date = log["created_at"].date()
                daily_activities[date] += 1

        # ストリーク計算
        streak = self._calculate_activity_streak(daily_activities)

        return {
            "total_activities": len(activity_logs),
            "unique_days": len(daily_activities),
            "avg_activities_per_day": statistics.mean(daily_activities.values())
            if daily_activities
            else 0,
            "activity_streak": streak,
            "max_daily_activities": max(daily_activities.values())
            if daily_activities
            else 0,
        }

    def _calculate_basebuilder_statistics(self, basebuilder_data: Dict) -> Dict:
        """BaseBuilder統計を計算"""
        word_proficiencies = basebuilder_data.get("word_proficiencies", [])
        category_performance = basebuilder_data.get("category_performance", [])

        if not word_proficiencies:
            avg_mastery = 0
            weak_words_count = 0
        else:
            mastery_levels = [wp["mastery_level"] for wp in word_proficiencies]
            avg_mastery = statistics.mean(mastery_levels) if mastery_levels else 0
            weak_words_count = sum(
                1 for wp in word_proficiencies if wp["mastery_level"] < 3
            )

        return {
            "total_words_studied": len(word_proficiencies),
            "avg_mastery_level": avg_mastery,
            "weak_words_count": weak_words_count,
            "category_performance_summary": {
                cat["category_id"]: {
                    "accuracy": cat["accuracy"],
                    "attempts": cat["total_answers"],
                }
                for cat in category_performance
            },
        }

    def _get_performance_level(self, accuracy: float) -> str:
        """精度から成績レベルを判定"""
        if accuracy >= 0.9:
            return "excellent"
        elif accuracy >= 0.8:
            return "good"
        elif accuracy >= 0.7:
            return "average"
        elif accuracy >= 0.6:
            return "below_average"
        else:
            return "poor"

    def _get_mastery_status(self, accuracy: float, difficulty: int) -> str:
        """精度と難易度から習熟状態を判定"""
        threshold = 0.8 - (difficulty - 1) * 0.05  # 難易度が高いほど閾値を下げる

        if accuracy >= threshold:
            return "mastered"
        elif accuracy >= threshold - 0.1:
            return "nearly_mastered"
        else:
            return "needs_practice"

    def _calculate_activity_streak(self, daily_activities: Dict) -> int:
        """活動ストリークを計算"""
        if not daily_activities:
            return 0

        today = datetime.now().date()
        streak = 0
        current_date = today

        while current_date in daily_activities:
            streak += 1
            current_date -= timedelta(days=1)

        # 今日活動がない場合は昨日からチェック
        if streak == 0 and (today - timedelta(days=1)) in daily_activities:
            current_date = today - timedelta(days=1)
            while current_date in daily_activities:
                streak += 1
                current_date -= timedelta(days=1)

        return streak

    def _get_empty_statistics(self) -> Dict[str, Any]:
        """空の統計構造を返す"""
        return {
            "calculation_date": datetime.now(),
            "answer_statistics": {
                "total_answers": 0,
                "correct_answers": 0,
                "accuracy_rate": 0.0,
                "avg_response_time": 0.0,
            },
            "category_statistics": {},
            "time_statistics": {
                "hourly_performance": {},
                "daily_performance": {},
                "best_performance_hour": None,
                "best_hour_accuracy": 0,
            },
            "difficulty_statistics": {},
            "unit_statistics": {
                "total_units": 0,
                "completed_units": 0,
                "in_progress_units": 0,
                "not_started_units": 0,
                "completion_rate": 0,
                "avg_progress": 0,
                "median_progress": 0,
            },
            "activity_statistics": {
                "total_activities": 0,
                "avg_activities_per_day": 0,
                "activity_streak": 0,
            },
            "basebuilder_statistics": {
                "total_words_studied": 0,
                "avg_mastery_level": 0,
                "weak_words_count": 0,
                "category_performance_summary": {},
            },
        }
