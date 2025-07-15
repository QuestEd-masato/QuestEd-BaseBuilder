"""
Weakness Pattern Analyzer
========================
パターン認識専門モジュール

責任:
- 学習パターンの識別
- エラーパターンの分析
- 時系列トレンドの検出
"""

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app


class WeaknessPatternAnalyzer:
    """パターン分析クラス"""

    def analyze_patterns(
        self, learning_data: Dict[str, Any], statistics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        学習データからパターンを分析

        Args:
            learning_data: 収集された学習データ
            statistics: 計算された統計情報

        Returns:
            dict: 識別されたパターン
        """
        try:
            patterns = {
                "analysis_date": datetime.now(),
                "error_patterns": self._analyze_error_patterns(
                    learning_data.get("answer_records", [])
                ),
                "time_patterns": self._analyze_time_patterns(
                    learning_data.get("answer_records", []),
                    statistics.get("time_statistics", {}),
                ),
                "difficulty_patterns": self._analyze_difficulty_patterns(
                    learning_data.get("answer_records", []),
                    statistics.get("difficulty_statistics", {}),
                ),
                "learning_curve_patterns": self._analyze_learning_curves(
                    learning_data.get("answer_records", [])
                ),
                "concept_patterns": self._analyze_concept_patterns(
                    learning_data.get("answer_records", [])
                ),
                "engagement_patterns": self._analyze_engagement_patterns(
                    learning_data.get("activity_logs", []),
                    learning_data.get("answer_records", []),
                ),
                "weakness_clusters": self._identify_weakness_clusters(
                    learning_data, statistics
                ),
            }

            current_app.logger.info(
                f"Analyzed patterns for student {learning_data.get('student_id')}"
            )

            return patterns

        except Exception as e:
            current_app.logger.error(f"Error analyzing patterns: {str(e)}")
            return self._get_empty_patterns()

    def _analyze_error_patterns(self, answer_records: List[Dict]) -> Dict:
        """エラーパターンを分析"""
        error_types = defaultdict(list)
        consecutive_errors = []
        current_streak = 0

        for i, record in enumerate(answer_records):
            if not record["is_correct"]:
                current_streak += 1

                # エラータイプを分類
                error_type = self._classify_error_type(record, answer_records, i)
                error_types[error_type].append(record)
            else:
                if current_streak > 0:
                    consecutive_errors.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            consecutive_errors.append(current_streak)

        # 最も頻繁なエラーパターンを特定
        common_patterns = []
        for error_type, records in error_types.items():
            if len(records) >= 3:  # 3回以上発生したパターン
                common_patterns.append(
                    {
                        "type": error_type,
                        "frequency": len(records),
                        "examples": records[:3],  # 最初の3例
                    }
                )

        return {
            "error_type_distribution": {k: len(v) for k, v in error_types.items()},
            "common_patterns": sorted(
                common_patterns, key=lambda x: x["frequency"], reverse=True
            ),
            "max_consecutive_errors": max(consecutive_errors)
            if consecutive_errors
            else 0,
            "avg_error_streak": statistics.mean(consecutive_errors)
            if consecutive_errors
            else 0,
        }

    def _analyze_time_patterns(
        self, answer_records: List[Dict], time_statistics: Dict
    ) -> Dict:
        """時間パターンを分析"""
        # 時間帯による成績変動
        hourly_variance = []
        for hour_data in time_statistics.get("hourly_performance", {}).values():
            if hour_data["total"] > 0:
                accuracy = hour_data["correct"] / hour_data["total"]
                hourly_variance.append(accuracy)

        performance_variance = (
            statistics.variance(hourly_variance) if len(hourly_variance) > 1 else 0
        )

        # 疲労パターンの検出
        fatigue_pattern = self._detect_fatigue_pattern(answer_records)

        # 最適学習時間の推定
        optimal_session_length = self._estimate_optimal_session_length(answer_records)

        return {
            "performance_variance_by_time": performance_variance,
            "shows_time_dependency": performance_variance > 0.05,
            "fatigue_pattern": fatigue_pattern,
            "optimal_session_length_minutes": optimal_session_length,
            "best_performance_time": time_statistics.get("best_performance_hour"),
        }

    def _analyze_difficulty_patterns(
        self, answer_records: List[Dict], difficulty_statistics: Dict
    ) -> Dict:
        """難易度パターンを分析"""
        # 難易度別の成功率勾配
        difficulty_gradient = []
        for level in sorted(difficulty_statistics.keys()):
            stat = difficulty_statistics[level]
            if stat["total_attempts"] > 0:
                difficulty_gradient.append(stat["accuracy_rate"])

        # 理想的な勾配からの逸脱を検出
        expected_gradient = [0.9 - i * 0.15 for i in range(len(difficulty_gradient))]
        deviation = sum(
            abs(a - e) for a, e in zip(difficulty_gradient, expected_gradient)
        )

        # 難易度ジャンプの検出
        difficulty_jumps = self._detect_difficulty_jumps(answer_records)

        return {
            "difficulty_gradient": difficulty_gradient,
            "shows_normal_progression": deviation < 0.3,
            "gradient_deviation": deviation,
            "difficulty_jumps": difficulty_jumps,
            "recommended_difficulty": self._recommend_difficulty_level(
                difficulty_statistics
            ),
        }

    def _analyze_learning_curves(self, answer_records: List[Dict]) -> Dict:
        """学習曲線パターンを分析"""
        if not answer_records:
            return {
                "curve_type": "insufficient_data",
                "improvement_rate": 0,
                "plateau_detected": False,
            }

        # 時系列で正答率を計算
        time_windows = self._create_time_windows(answer_records, window_size=7)
        window_accuracies = []

        for window in time_windows:
            if len(window) > 0:
                accuracy = sum(1 for r in window if r["is_correct"]) / len(window)
                window_accuracies.append(accuracy)

        if len(window_accuracies) < 2:
            return {
                "curve_type": "insufficient_data",
                "improvement_rate": 0,
                "plateau_detected": False,
            }

        # 改善率を計算
        improvement_rate = (window_accuracies[-1] - window_accuracies[0]) / len(
            window_accuracies
        )

        # プラトー検出
        plateau_detected = self._detect_plateau(window_accuracies)

        # 学習曲線タイプを分類
        curve_type = self._classify_learning_curve(window_accuracies)

        return {
            "curve_type": curve_type,
            "improvement_rate": improvement_rate,
            "plateau_detected": plateau_detected,
            "weekly_accuracies": window_accuracies,
        }

    def _analyze_concept_patterns(self, answer_records: List[Dict]) -> Dict:
        """概念理解パターンを分析"""
        concept_errors = defaultdict(lambda: {"total": 0, "errors": 0})

        for record in answer_records:
            if record.get("problem") and record["problem"].get("content"):
                # 問題文から概念キーワードを抽出（簡易版）
                concepts = self._extract_concepts(record["problem"]["content"])

                for concept in concepts:
                    concept_errors[concept]["total"] += 1
                    if not record["is_correct"]:
                        concept_errors[concept]["errors"] += 1

        # 弱点概念を特定
        weak_concepts = []
        for concept, data in concept_errors.items():
            if data["total"] >= 3:  # 最低3回出現
                error_rate = data["errors"] / data["total"]
                if error_rate > 0.4:  # エラー率40%以上
                    weak_concepts.append(
                        {
                            "concept": concept,
                            "error_rate": error_rate,
                            "occurrences": data["total"],
                        }
                    )

        return {
            "identified_concepts": len(concept_errors),
            "weak_concepts": sorted(
                weak_concepts, key=lambda x: x["error_rate"], reverse=True
            ),
            "concept_mastery_distribution": self._calculate_concept_mastery_distribution(
                concept_errors
            ),
        }

    def _analyze_engagement_patterns(
        self, activity_logs: List[Dict], answer_records: List[Dict]
    ) -> Dict:
        """エンゲージメントパターンを分析"""
        # 日別の活動量
        daily_engagement = defaultdict(lambda: {"activities": 0, "answers": 0})

        for log in activity_logs:
            if log.get("created_at"):
                date = log["created_at"].date()
                daily_engagement[date]["activities"] += 1

        for record in answer_records:
            if record.get("created_at"):
                date = record["created_at"].date()
                daily_engagement[date]["answers"] += 1

        # エンゲージメントの一貫性を評価
        engagement_scores = [
            data["activities"] + data["answers"] for data in daily_engagement.values()
        ]

        consistency = (
            1
            - (statistics.stdev(engagement_scores) / statistics.mean(engagement_scores))
            if len(engagement_scores) > 1 and statistics.mean(engagement_scores) > 0
            else 0
        )

        # 学習パターンを分類
        pattern_type = self._classify_engagement_pattern(daily_engagement)

        return {
            "engagement_consistency": consistency,
            "pattern_type": pattern_type,
            "avg_daily_engagement": statistics.mean(engagement_scores)
            if engagement_scores
            else 0,
            "peak_engagement_days": self._find_peak_days(daily_engagement),
        }

    def _identify_weakness_clusters(
        self, learning_data: Dict[str, Any], statistics: Dict[str, Any]
    ) -> List[Dict]:
        """弱点クラスターを特定"""
        clusters = []

        # カテゴリベースのクラスター
        for cat_id, cat_stats in statistics.get("category_statistics", {}).items():
            if cat_stats["accuracy_rate"] < 0.6 and cat_stats["total_attempts"] >= 10:
                clusters.append(
                    {
                        "type": "category",
                        "identifier": cat_id,
                        "severity": 1 - cat_stats["accuracy_rate"],
                        "evidence_count": cat_stats["total_attempts"],
                    }
                )

        # 難易度ベースのクラスター
        for level, diff_stats in statistics.get("difficulty_statistics", {}).items():
            if (
                diff_stats["mastery_status"] == "needs_practice"
                and diff_stats["total_attempts"] >= 5
            ):
                clusters.append(
                    {
                        "type": "difficulty",
                        "identifier": f"level_{level}",
                        "severity": 1 - diff_stats["accuracy_rate"],
                        "evidence_count": diff_stats["total_attempts"],
                    }
                )

        return sorted(clusters, key=lambda x: x["severity"], reverse=True)

    # ヘルパーメソッド

    def _classify_error_type(self, record: Dict, all_records: List, index: int) -> str:
        """エラータイプを分類"""
        # 簡易的な分類ロジック
        if index > 0 and not all_records[index - 1]["is_correct"]:
            return "consecutive_error"

        if record.get("response_time", 0) < 5:
            return "rushed_answer"

        if record.get("response_time", 0) > 120:
            return "overthinking"

        problem = record.get("problem", {})
        if problem.get("difficulty_level", 1) > 3:
            return "high_difficulty_error"

        return "general_error"

    def _detect_fatigue_pattern(self, answer_records: List[Dict]) -> Dict:
        """疲労パターンを検出"""
        session_chunks = self._split_into_sessions(answer_records)
        fatigue_indicators = []

        for session in session_chunks:
            if len(session) >= 10:
                # セッション内での正答率の変化
                first_half = session[: len(session) // 2]
                second_half = session[len(session) // 2 :]

                first_accuracy = sum(1 for r in first_half if r["is_correct"]) / len(
                    first_half
                )
                second_accuracy = sum(1 for r in second_half if r["is_correct"]) / len(
                    second_half
                )

                if first_accuracy - second_accuracy > 0.2:
                    fatigue_indicators.append(True)
                else:
                    fatigue_indicators.append(False)

        shows_fatigue = (
            sum(fatigue_indicators) / len(fatigue_indicators) > 0.5
            if fatigue_indicators
            else False
        )

        return {
            "shows_fatigue_pattern": shows_fatigue,
            "fatigue_onset_problems": 15 if shows_fatigue else None,
        }

    def _estimate_optimal_session_length(self, answer_records: List[Dict]) -> int:
        """最適なセッション長を推定"""
        session_chunks = self._split_into_sessions(answer_records)
        optimal_lengths = []

        for session in session_chunks:
            if len(session) >= 5:
                # 高い正答率を維持している長さを見つける
                for i in range(5, len(session)):
                    window = session[i - 5 : i]
                    accuracy = sum(1 for r in window if r["is_correct"]) / 5
                    if accuracy < 0.7:
                        optimal_lengths.append(i - 5)
                        break
                else:
                    optimal_lengths.append(len(session))

        if optimal_lengths:
            # 平均回答時間を考慮して分に変換
            avg_problems = statistics.median(optimal_lengths)
            return int(avg_problems * 2)  # 1問あたり2分と仮定

        return 30  # デフォルト30分

    def _detect_difficulty_jumps(self, answer_records: List[Dict]) -> List[Dict]:
        """難易度ジャンプを検出"""
        jumps = []

        for i in range(1, len(answer_records)):
            prev_difficulty = (
                answer_records[i - 1].get("problem", {}).get("difficulty_level", 1)
            )
            curr_difficulty = (
                answer_records[i].get("problem", {}).get("difficulty_level", 1)
            )

            if curr_difficulty - prev_difficulty >= 2:
                jumps.append(
                    {
                        "position": i,
                        "from_level": prev_difficulty,
                        "to_level": curr_difficulty,
                        "success": answer_records[i]["is_correct"],
                    }
                )

        return jumps

    def _recommend_difficulty_level(self, difficulty_statistics: Dict) -> int:
        """推奨難易度レベルを決定"""
        for level in sorted(difficulty_statistics.keys()):
            stat = difficulty_statistics[level]
            if stat["accuracy_rate"] >= 0.7 and stat["total_attempts"] >= 5:
                # 70%以上の正答率なら次のレベルを推奨
                return min(level + 1, 5)

        return 1  # デフォルトは最低レベル

    def _create_time_windows(
        self, records: List[Dict], window_size: int
    ) -> List[List[Dict]]:
        """時間窓を作成"""
        if not records:
            return []

        windows = []
        current_window = []
        window_start = records[0]["created_at"].date()

        for record in records:
            record_date = record["created_at"].date()
            if (record_date - window_start).days < window_size:
                current_window.append(record)
            else:
                if current_window:
                    windows.append(current_window)
                current_window = [record]
                window_start = record_date

        if current_window:
            windows.append(current_window)

        return windows

    def _detect_plateau(self, accuracies: List[float]) -> bool:
        """プラトー（停滞期）を検出"""
        if len(accuracies) < 3:
            return False

        # 最後の3つの値の変動をチェック
        recent_values = accuracies[-3:]
        variance = statistics.variance(recent_values)

        return variance < 0.01  # 変動が1%未満

    def _classify_learning_curve(self, accuracies: List[float]) -> str:
        """学習曲線を分類"""
        if len(accuracies) < 2:
            return "insufficient_data"

        improvement = accuracies[-1] - accuracies[0]

        if improvement > 0.2:
            return "rapid_improvement"
        elif improvement > 0.1:
            return "steady_improvement"
        elif improvement > -0.1:
            return "plateau"
        else:
            return "declining"

    def _extract_concepts(self, problem_content: str) -> List[str]:
        """問題文から概念を抽出（簡易版）"""
        # 実際の実装では自然言語処理を使用
        keywords = ["計算", "文法", "単語", "理解", "応用", "分析"]
        found_concepts = []

        for keyword in keywords:
            if keyword in problem_content:
                found_concepts.append(keyword)

        return found_concepts if found_concepts else ["一般"]

    def _calculate_concept_mastery_distribution(self, concept_errors: Dict) -> Dict:
        """概念習熟度分布を計算"""
        distribution = {"mastered": 0, "learning": 0, "struggling": 0}

        for concept, data in concept_errors.items():
            if data["total"] > 0:
                error_rate = data["errors"] / data["total"]
                if error_rate < 0.2:
                    distribution["mastered"] += 1
                elif error_rate < 0.5:
                    distribution["learning"] += 1
                else:
                    distribution["struggling"] += 1

        return distribution

    def _classify_engagement_pattern(self, daily_engagement: Dict) -> str:
        """エンゲージメントパターンを分類"""
        if not daily_engagement:
            return "no_engagement"

        total_days = len(daily_engagement)
        active_days = sum(
            1
            for data in daily_engagement.values()
            if data["activities"] + data["answers"] > 0
        )

        engagement_rate = active_days / total_days

        if engagement_rate > 0.8:
            return "highly_consistent"
        elif engagement_rate > 0.5:
            return "moderately_consistent"
        elif engagement_rate > 0.2:
            return "sporadic"
        else:
            return "minimal"

    def _find_peak_days(self, daily_engagement: Dict) -> List[int]:
        """ピーク活動曜日を見つける"""
        weekday_totals = defaultdict(int)

        for date, data in daily_engagement.items():
            weekday = date.weekday()
            weekday_totals[weekday] += data["activities"] + data["answers"]

        if not weekday_totals:
            return []

        max_activity = max(weekday_totals.values())
        return [
            day for day, total in weekday_totals.items() if total >= max_activity * 0.8
        ]

    def _split_into_sessions(self, answer_records: List[Dict]) -> List[List[Dict]]:
        """回答記録をセッションに分割"""
        if not answer_records:
            return []

        sessions = []
        current_session = [answer_records[0]]

        for i in range(1, len(answer_records)):
            time_diff = (
                answer_records[i]["created_at"] - answer_records[i - 1]["created_at"]
            ).total_seconds()

            if time_diff > 1800:  # 30分以上の間隔
                sessions.append(current_session)
                current_session = [answer_records[i]]
            else:
                current_session.append(answer_records[i])

        if current_session:
            sessions.append(current_session)

        return sessions

    def _get_empty_patterns(self) -> Dict[str, Any]:
        """空のパターン構造を返す"""
        return {
            "analysis_date": datetime.now(),
            "error_patterns": {
                "error_type_distribution": {},
                "common_patterns": [],
                "max_consecutive_errors": 0,
                "avg_error_streak": 0,
            },
            "time_patterns": {
                "performance_variance_by_time": 0,
                "shows_time_dependency": False,
                "fatigue_pattern": {"shows_fatigue_pattern": False},
                "optimal_session_length_minutes": 30,
            },
            "difficulty_patterns": {
                "difficulty_gradient": [],
                "shows_normal_progression": True,
                "gradient_deviation": 0,
                "difficulty_jumps": [],
            },
            "learning_curve_patterns": {
                "curve_type": "insufficient_data",
                "improvement_rate": 0,
                "plateau_detected": False,
            },
            "concept_patterns": {
                "identified_concepts": 0,
                "weak_concepts": [],
                "concept_mastery_distribution": {},
            },
            "engagement_patterns": {
                "engagement_consistency": 0,
                "pattern_type": "no_engagement",
                "avg_daily_engagement": 0,
            },
            "weakness_clusters": [],
        }
