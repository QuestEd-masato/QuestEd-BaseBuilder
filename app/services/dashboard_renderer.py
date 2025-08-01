"""
ダッシュボードレンダリングサービス
Phase6-B: 各セクションレンダリング関数をサービス層に移行
"""

import logging
from typing import Any, Dict

from flask import render_template_string

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class DashboardRendererService(BaseService):
    """ダッシュボードレンダリングサービス
    
    Phase6-B: dashboard.py の各_render_*_section関数から移行
    Single Responsibility: ダッシュボードセクションのHTML生成
    """
    
    def __init__(self):
        super().__init__()
    
    def render_milestone_section(self, milestone_data: Dict[str, Any]) -> str:
        """マイルストーンセクションをレンダリング"""
        try:
            if milestone_data.get('status') == 'error':
                return self._render_error_section('マイルストーン', milestone_data.get('error', '不明なエラー'))
            
            template = """
            <div class="milestone-section">
                <h3>マイルストーン進捗</h3>
                <div class="progress-summary">
                    <div class="stat-item">
                        <span class="stat-value">{{ completed }}/{{ total }}</span>
                        <span class="stat-label">完了マイルストーン</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ completion_rate }}%"></div>
                    </div>
                    <span class="progress-text">{{ completion_rate|round(1) }}% 完了</span>
                </div>
                
                {% if recent_completed %}
                <div class="recent-milestones">
                    <h4>最近完了したマイルストーン</h4>
                    <ul>
                    {% for milestone in recent_completed %}
                        <li>
                            <span class="milestone-title">{{ milestone.title }}</span>
                            <span class="milestone-date">{{ milestone.completed_at.strftime('%m/%d') }}</span>
                        </li>
                    {% endfor %}
                    </ul>
                </div>
                {% endif %}
                
                {% if next_milestone %}
                <div class="next-milestone">
                    <h4>次のマイルストーン</h4>
                    <div class="milestone-card">
                        <span class="milestone-title">{{ next_milestone.title }}</span>
                        <div class="progress-mini">
                            <div class="progress-fill" style="width: {{ next_milestone.progress }}%"></div>
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **milestone_data)
            
        except Exception as e:
            logger.error(f"Error rendering milestone section: {str(e)}")
            return self._render_error_section('マイルストーン', str(e))
    
    def render_quiz_history_section(self, quiz_data: Dict[str, Any]) -> str:
        """クイズ履歴セクションをレンダリング"""
        try:
            if quiz_data.get('status') == 'error':
                return self._render_error_section('クイズ履歴', quiz_data.get('error', '不明なエラー'))
            
            template = """
            <div class="quiz-history-section">
                <h3>クイズ履歴</h3>
                <div class="quiz-stats">
                    <div class="stat-item">
                        <span class="stat-value">{{ total_quizzes }}</span>
                        <span class="stat-label">総クイズ数</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{ average_score|round(1) }}</span>
                        <span class="stat-label">平均スコア</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{ best_score }}</span>
                        <span class="stat-label">最高スコア</span>
                    </div>
                </div>
                
                <div class="trend-indicator trend-{{ improvement_trend }}">
                    {% if improvement_trend == 'improving' %}
                        <span class="trend-icon">📈</span> 向上中
                    {% elif improvement_trend == 'declining' %}
                        <span class="trend-icon">📉</span> 要改善
                    {% else %}
                        <span class="trend-icon">📊</span> 安定
                    {% endif %}
                </div>
                
                {% if recent_quizzes %}
                <div class="recent-quiz-list">
                    <h4>最近のクイズ</h4>
                    <ul>
                    {% for quiz in recent_quizzes[:5] %}
                        <li>
                            <span class="quiz-subject">{{ quiz.subject }}</span>
                            <span class="quiz-score">{{ quiz.score }}/{{ quiz.max_score }}</span>
                            <span class="quiz-date">{{ quiz.date.strftime('%m/%d') }}</span>
                        </li>
                    {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **quiz_data)
            
        except Exception as e:
            logger.error(f"Error rendering quiz history section: {str(e)}")
            return self._render_error_section('クイズ履歴', str(e))
    
    def render_progress_summary_section(self, progress_data: Dict[str, Any]) -> str:
        """進捗サマリーセクションをレンダリング"""
        try:
            if progress_data.get('status') == 'error':
                return self._render_error_section('進捗サマリー', progress_data.get('error', '不明なエラー'))
            
            template = """
            <div class="progress-summary-section">
                <h3>学習進捗サマリー</h3>
                <div class="progress-grid">
                    <div class="progress-item">
                        <div class="progress-circle">
                            <span class="progress-percentage">{{ completion_percentage|round(0) }}%</span>
                        </div>
                        <span class="progress-label">カリキュラム進捗</span>
                        <span class="progress-detail">{{ completed_units }}/{{ total_curriculum_units }} 単元</span>
                    </div>
                    
                    <div class="activity-stats">
                        <div class="stat-row">
                            <span class="stat-label">今月のアクティビティ</span>
                            <span class="stat-value">{{ monthly_activities }}</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">学習ストリーク</span>
                            <span class="stat-value">{{ learning_streak_days }}日</span>
                        </div>
                    </div>
                </div>
                
                {% if estimated_completion_date %}
                <div class="completion-estimate">
                    <span class="estimate-label">推定完了日:</span>
                    <span class="estimate-date">{{ estimated_completion_date.strftime('%Y年%m月') }}</span>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **progress_data)
            
        except Exception as e:
            logger.error(f"Error rendering progress summary section: {str(e)}")
            return self._render_error_section('進捗サマリー', str(e))
    
    def render_ai_recommendation_section(self, ai_data: Dict[str, Any]) -> str:
        """AI推薦セクションをレンダリング"""
        try:
            if ai_data.get('status') == 'error':
                return self._render_error_section('AI推薦', ai_data.get('error', '不明なエラー'))
            
            template = """
            <div class="ai-recommendation-section">
                <h3>AI推薦</h3>
                
                {% if recommendations %}
                <div class="recommendation-summary">
                    <span class="pending-count">{{ pending_recommendations }}</span>件の新しい推薦があります
                </div>
                
                <div class="recommendation-list">
                    {% for rec in recommendations %}
                    <div class="recommendation-item priority-{{ rec.priority }}">
                        <div class="rec-header">
                            <span class="rec-type">{{ rec.type }}</span>
                            <span class="rec-priority">{{ rec.priority }}</span>
                        </div>
                        <div class="rec-content">
                            <p>{{ rec.title }}</p>
                        </div>
                        <div class="rec-footer">
                            <span class="rec-date">{{ rec.created_at.strftime('%m/%d') }}</span>
                            {% if rec.is_applied %}
                                <span class="rec-status applied">適用済み</span>
                            {% else %}
                                <span class="rec-status pending">未適用</span>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="no-recommendations">
                    <p>現在、新しい推薦はありません。</p>
                    <p>学習を続けると、パーソナライズされた推薦が表示されます。</p>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **ai_data)
            
        except Exception as e:
            logger.error(f"Error rendering AI recommendation section: {str(e)}")
            return self._render_error_section('AI推薦', str(e))
    
    def render_recent_activities_section(self, activity_data: Dict[str, Any]) -> str:
        """最近のアクティビティセクションをレンダリング"""
        try:
            if activity_data.get('status') == 'error':
                return self._render_error_section('最近のアクティビティ', activity_data.get('error', '不明なエラー'))
            
            template = """
            <div class="recent-activities-section">
                <h3>最近のアクティビティ</h3>
                
                {% if activities %}
                <div class="activity-summary">
                    <span class="activity-count">{{ total_activities }}</span>件のアクティビティ
                    {% if last_activity %}
                        <span class="last-activity">最終: {{ last_activity.strftime('%m/%d %H:%M') }}</span>
                    {% endif %}
                </div>
                
                <div class="activity-timeline">
                    {% for activity in activities %}
                    <div class="activity-item type-{{ activity.type }}">
                        <div class="activity-icon">{{ activity.icon }}</div>
                        <div class="activity-content">
                            <div class="activity-title">{{ activity.title }}</div>
                            <div class="activity-description">{{ activity.description }}</div>
                        </div>
                        <div class="activity-timestamp">
                            {{ activity.timestamp.strftime('%m/%d %H:%M') }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="no-activities">
                    <p>まだアクティビティがありません。</p>
                    <p>学習を始めると、ここにアクティビティが表示されます。</p>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **activity_data)
            
        except Exception as e:
            logger.error(f"Error rendering recent activities section: {str(e)}")
            return self._render_error_section('最近のアクティビティ', str(e))
    
    def render_basebuilder_section(self, bb_data: Dict[str, Any]) -> str:
        """BaseBuilderセクションをレンダリング"""
        try:
            if bb_data.get('status') == 'error':
                return self._render_error_section('BaseBuilder', bb_data.get('error', '不明なエラー'))
            
            if bb_data.get('status') == 'no_data':
                template = """
                <div class="basebuilder-section">
                    <h3>BaseBuilder 語彙学習</h3>
                    <div class="no-data-message">
                        <p>BaseBuilderの学習データがまだありません。</p>
                        <p>語彙学習を始めてみましょう！</p>
                        <a href="/basebuilder" class="start-button">BaseBuilderを始める</a>
                    </div>
                </div>
                """
                return render_template_string(template)
            
            template = """
            <div class="basebuilder-section">
                <h3>BaseBuilder 語彙学習</h3>
                <div class="vocabulary-stats">
                    <div class="stat-item">
                        <span class="stat-value">{{ total_words_learned }}</span>
                        <span class="stat-label">学習済み単語</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{ vocabulary_accuracy|round(1) }}%</span>
                        <span class="stat-label">正解率</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{ vocabulary_level }}</span>
                        <span class="stat-label">語彙レベル</span>
                    </div>
                </div>
                
                {% if recent_sessions %}
                <div class="recent-sessions">
                    <h4>最近のセッション</h4>
                    <ul>
                    {% for session in recent_sessions %}
                        <li>
                            <span class="session-date">{{ session.date.strftime('%m/%d') }}</span>
                            <span class="session-words">{{ session.words_learned }}語</span>
                            <span class="session-accuracy">{{ session.accuracy|round(1) }}%</span>
                        </li>
                    {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            """
            
            return render_template_string(template, **bb_data)
            
        except Exception as e:
            logger.error(f"Error rendering BaseBuilder section: {str(e)}")
            return self._render_error_section('BaseBuilder', str(e))
    
    def render_vocabulary_analysis_section(self, vocab_data: Dict[str, Any]) -> str:
        """語彙分析セクションをレンダリング"""
        try:
            if vocab_data.get('status') == 'pending_implementation':
                template = """
                <div class="vocabulary-analysis-section">
                    <h3>語彙分析</h3>
                    <div class="pending-implementation">
                        <p>語彙分析機能は準備中です。</p>
                        <p>近日中に詳細な語彙分析結果をご提供予定です。</p>
                    </div>
                </div>
                """
                return render_template_string(template)
            
            return self._render_error_section('語彙分析', '実装準備中')
            
        except Exception as e:
            logger.error(f"Error rendering vocabulary analysis section: {str(e)}")
            return self._render_error_section('語彙分析', str(e))
    
    def render_spaced_repetition_section(self, sr_data: Dict[str, Any]) -> str:
        """間隔反復学習セクションをレンダリング"""
        try:
            if sr_data.get('status') == 'pending_implementation':
                template = """
                <div class="spaced-repetition-section">
                    <h3>間隔反復学習</h3>
                    <div class="pending-implementation">
                        <p>間隔反復学習機能は準備中です。</p>
                        <p>効率的な復習スケジュールを近日中にご提供予定です。</p>
                    </div>
                </div>
                """
                return render_template_string(template)
            
            return self._render_error_section('間隔反復学習', '実装準備中')
            
        except Exception as e:
            logger.error(f"Error rendering spaced repetition section: {str(e)}")
            return self._render_error_section('間隔反復学習', str(e))
    
    def render_weakness_analysis_section(self, weakness_data: Dict[str, Any]) -> str:
        """弱点分析セクションをレンダリング"""
        try:
            if weakness_data.get('status') == 'pending_implementation':
                template = """
                <div class="weakness-analysis-section">
                    <h3>弱点分析</h3>
                    <div class="pending-implementation">
                        <p>弱点分析機能は準備中です。</p>
                        <p>個人に最適化された弱点分析を近日中にご提供予定です。</p>
                    </div>
                </div>
                """
                return render_template_string(template)
            
            return self._render_error_section('弱点分析', '実装準備中')
            
        except Exception as e:
            logger.error(f"Error rendering weakness analysis section: {str(e)}")
            return self._render_error_section('弱点分析', str(e))
    
    def render_chart_data_section(self, chart_data: Dict[str, Any]) -> str:
        """チャートデータセクションをレンダリング"""
        try:
            if chart_data.get('status') == 'error':
                return self._render_error_section('学習チャート', chart_data.get('error', '不明なエラー'))
            
            template = """
            <div class="chart-data-section">
                <h3>学習チャート</h3>
                
                <div class="chart-container">
                    {% if chart_data.progress_chart.labels %}
                    <div class="chart-item">
                        <h4>学習進捗チャート</h4>
                        <div class="chart-placeholder" data-chart-type="line" 
                             data-labels="{{ chart_data.progress_chart.labels|join(',') }}"
                             data-values="{{ chart_data.progress_chart.data|join(',') }}">
                            [進捗チャートがここに表示されます]
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if chart_data.score_trend_chart.labels %}
                    <div class="chart-item">
                        <h4>スコア推移チャート</h4>
                        <div class="chart-placeholder" data-chart-type="line"
                             data-labels="{{ chart_data.score_trend_chart.labels|join(',') }}"
                             data-values="{{ chart_data.score_trend_chart.data|join(',') }}">
                            [スコアチャートがここに表示されます]
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            """
            
            return render_template_string(template, chart_data=chart_data)
            
        except Exception as e:
            logger.error(f"Error rendering chart data section: {str(e)}")
            return self._render_error_section('学習チャート', str(e))
    
    def _render_error_section(self, section_name: str, error_message: str) -> str:
        """エラーセクションをレンダリング"""
        template = """
        <div class="error-section">
            <h3>{{ section_name }}</h3>
            <div class="error-message">
                <span class="error-icon">⚠️</span>
                <p>{{ section_name }}の読み込み中にエラーが発生しました。</p>
                <details>
                    <summary>詳細情報</summary>
                    <p>{{ error_message }}</p>
                </details>
            </div>
        </div>
        """
        
        return render_template_string(
            template, 
            section_name=section_name, 
            error_message=error_message
        )
    
    def render_complete_dashboard(self, dashboard_data: Dict[str, Any]) -> Dict[str, str]:
        """完全なダッシュボードセクションを全てレンダリング"""
        try:
            rendered_sections = {}
            
            # 各セクションをレンダリング
            rendered_sections['milestone_section'] = self.render_milestone_section(
                dashboard_data.get('milestone_data', {})
            )
            
            rendered_sections['quiz_history_section'] = self.render_quiz_history_section(
                dashboard_data.get('quiz_history', {})
            )
            
            rendered_sections['progress_summary_section'] = self.render_progress_summary_section(
                dashboard_data.get('progress_summary', {})
            )
            
            rendered_sections['ai_recommendation_section'] = self.render_ai_recommendation_section(
                dashboard_data.get('ai_recommendations', {})
            )
            
            rendered_sections['recent_activities_section'] = self.render_recent_activities_section(
                dashboard_data.get('recent_activities', {})
            )
            
            rendered_sections['basebuilder_section'] = self.render_basebuilder_section(
                dashboard_data.get('basebuilder_data', {})
            )
            
            rendered_sections['vocabulary_analysis_section'] = self.render_vocabulary_analysis_section(
                dashboard_data.get('vocabulary_analysis', {})
            )
            
            rendered_sections['spaced_repetition_section'] = self.render_spaced_repetition_section(
                dashboard_data.get('spaced_repetition', {})
            )
            
            rendered_sections['weakness_analysis_section'] = self.render_weakness_analysis_section(
                dashboard_data.get('weakness_analysis', {})
            )
            
            rendered_sections['chart_data_section'] = self.render_chart_data_section(
                dashboard_data.get('chart_data', {})
            )
            
            logger.info("Complete dashboard rendered successfully")
            return rendered_sections
            
        except Exception as e:
            logger.error(f"Error rendering complete dashboard: {str(e)}")
            
            # エラー時は全セクションをエラー表示
            error_sections = {}
            section_names = [
                'milestone_section', 'quiz_history_section', 'progress_summary_section',
                'ai_recommendation_section', 'recent_activities_section', 'basebuilder_section',
                'vocabulary_analysis_section', 'spaced_repetition_section', 
                'weakness_analysis_section', 'chart_data_section'
            ]
            
            for section_name in section_names:
                error_sections[section_name] = self._render_error_section(
                    section_name.replace('_section', '').replace('_', ' ').title(),
                    str(e)
                )
            
            return error_sections
    
    def _has_permission(self, user, action: str, resource: Any = None) -> bool:
        """
        権限チェック実装
        Phase8E緊急修正: BaseService抽象メソッド実装
        """
        # レンダリングサービスは認証されたユーザーが利用可能
        if user and hasattr(user, 'id'):
            return True
        return False