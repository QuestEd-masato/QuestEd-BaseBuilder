# -*- coding: utf-8 -*-
"""
Teacher Dashboard Service

教師ダッシュボード専門サービス
Phase8G: 教師専用機能の専門管理とPhase8D成果の最大活用
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from flask import current_app, render_template
from flask_login import current_user
from sqlalchemy import func, desc

from app.models import (
    Class, ClassEnrollment, User, Curriculum, CurriculumUnit,
    InquiryTheme, Milestone, ChatHistory, db
)

logger = logging.getLogger(__name__)


class TeacherDashboardService:
    """教師ダッシュボード専門サービス"""
    
    def __init__(self):
        """サービス初期化"""
        # Phase8D既存サービスとの統合
        from .dashboard_orchestration_service import DashboardOrchestrationService
        from app.services.student_dashboard.learning_progress_service import LearningProgressService
        from .activity_analytics_service import ActivityAnalyticsService
        from app.services.student_dashboard.basebuilder_analytics_service import BaseBuilderAnalyticsService as BaseBuilderIntegrationService
        from .student_dashboard_data_service import StudentDashboardDataService
        
        self.orchestration_service = DashboardOrchestrationService()
        self.learning_progress_service = LearningProgressService()
        self.activity_analytics_service = ActivityAnalyticsService()
        self.basebuilder_service = BaseBuilderIntegrationService()
        self.student_data_service = StudentDashboardDataService()
        
        logger.info("TeacherDashboardService initialized with Phase8D services integration")

    def build_complete_teacher_dashboard(self, teacher_id: int) -> Dict[str, Any]:
        """
        教師ダッシュボード完全構築
        
        Args:
            teacher_id: 教師ID
            
        Returns:
            Dict: 完全な教師ダッシュボードデータ
        """
        try:
            logger.info(f"Building complete teacher dashboard for teacher {teacher_id}")
            
            # 基本クラス情報
            teacher_classes = self._get_teacher_classes(teacher_id)
            
            # 教師専用統計
            teacher_statistics = self.generate_teacher_statistics(teacher_id, teacher_classes)
            
            # 学生進捗統合分析
            student_progress_analysis = self.analyze_student_progress(teacher_id, teacher_classes)
            
            # クラス管理情報
            class_management_data = self.get_class_management_data(teacher_id, teacher_classes)
            
            # 教師向け通知・アラート
            teacher_alerts = self.generate_teacher_alerts(teacher_id, teacher_classes)
            
            # Phase8D サービス統合データ
            integrated_analytics = self._integrate_phase8d_analytics(teacher_id, teacher_classes)
            
            dashboard_data = {
                'teacher_info': {
                    'teacher_id': teacher_id,
                    'classes': teacher_classes,
                    'total_students': sum(len(cls.get('students', [])) for cls in teacher_classes)
                },
                'teacher_statistics': teacher_statistics,
                'student_progress_analysis': student_progress_analysis,
                'class_management_data': class_management_data,
                'teacher_alerts': teacher_alerts,
                'integrated_analytics': integrated_analytics,
                'generated_at': datetime.now().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error building teacher dashboard for {teacher_id}: {str(e)}")
            return self._get_empty_dashboard_data()

    def generate_teacher_statistics(self, teacher_id: int, teacher_classes: List[Dict]) -> Dict[str, Any]:
        """
        教師専用統計生成
        
        Args:
            teacher_id: 教師ID
            teacher_classes: 教師のクラス一覧
            
        Returns:
            Dict: 教師専用統計データ
        """
        try:
            logger.info(f"Generating teacher statistics for teacher {teacher_id}")
            
            class_ids = [cls['id'] for cls in teacher_classes]
            
            # 基本統計
            basic_stats = {
                'total_classes': len(teacher_classes),
                'total_students': 0,
                'active_curriculums': 0,
                'pending_evaluations': 0
            }
            
            # クラス別統計
            class_statistics = []
            for class_info in teacher_classes:
                class_stats = self._generate_class_statistics(class_info['id'])
                class_statistics.append({
                    'class_id': class_info['id'],
                    'class_name': class_info['name'],
                    'stats': class_stats
                })
                basic_stats['total_students'] += class_stats.get('student_count', 0)
                basic_stats['active_curriculums'] += class_stats.get('curriculum_count', 0)
            
            # 教師パフォーマンス指標
            performance_metrics = self._calculate_teacher_performance_metrics(teacher_id, class_ids)
            
            # 週間・月間トレンド
            trend_analysis = self._analyze_teaching_trends(teacher_id, class_ids)
            
            return {
                'basic_stats': basic_stats,
                'class_statistics': class_statistics,
                'performance_metrics': performance_metrics,
                'trend_analysis': trend_analysis,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating teacher statistics: {str(e)}")
            return {'basic_stats': {}, 'class_statistics': []}

    def analyze_student_progress(self, teacher_id: int, teacher_classes: List[Dict]) -> Dict[str, Any]:
        """
        学生進捗統合分析
        
        Args:
            teacher_id: 教師ID
            teacher_classes: 教師のクラス一覧
            
        Returns:
            Dict: 学生進捗分析データ
        """
        try:
            logger.info(f"Analyzing student progress for teacher {teacher_id}")
            
            class_ids = [cls['id'] for cls in teacher_classes]
            
            # Phase8D学習進捗サービスとの統合
            progress_summary = []
            for class_id in class_ids:
                students = self._get_students_in_class(class_id)
                
                class_progress = {
                    'class_id': class_id,
                    'class_name': next(cls['name'] for cls in teacher_classes if cls['id'] == class_id),
                    'student_progress': []
                }
                
                for student in students:
                    # Phase8D学習進捗サービス活用
                    student_progress = self.learning_progress_service.get_student_comprehensive_progress(
                        student['id']
                    )
                    
                    class_progress['student_progress'].append({
                        'student_id': student['id'],
                        'student_name': student['name'],
                        'progress_data': student_progress
                    })
                
                progress_summary.append(class_progress)
            
            # 進捗分析
            analysis_results = self._analyze_progress_patterns(progress_summary)
            
            # 改善提案
            improvement_suggestions = self._generate_improvement_suggestions(analysis_results)
            
            return {
                'progress_summary': progress_summary,
                'analysis_results': analysis_results,
                'improvement_suggestions': improvement_suggestions,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing student progress: {str(e)}")
            return {'progress_summary': [], 'analysis_results': {}}

    def get_class_management_data(self, teacher_id: int, teacher_classes: List[Dict]) -> Dict[str, Any]:
        """
        クラス管理データ取得
        
        Args:
            teacher_id: 教師ID
            teacher_classes: 教師のクラス一覧
            
        Returns:
            Dict: クラス管理データ
        """
        try:
            logger.info(f"Getting class management data for teacher {teacher_id}")
            
            management_data = {
                'curriculum_management': [],
                'milestone_tracking': [],
                'inquiry_themes': [],
                'recent_activities': []
            }
            
            for class_info in teacher_classes:
                class_id = class_info['id']
                
                # カリキュラム管理状況
                curricula = Curriculum.query.filter_by(
                    class_id=class_id, created_by=teacher_id
                ).all()
                
                curriculum_info = []
                for curriculum in curricula:
                    curriculum_info.append({
                        'id': curriculum.id,
                        'title': curriculum.title,
                        'status': self._determine_curriculum_status(curriculum),
                        'completion_rate': self._calculate_curriculum_completion_rate(curriculum.id),
                        'last_updated': curriculum.updated_at.isoformat() if curriculum.updated_at else None
                    })
                
                management_data['curriculum_management'].append({
                    'class_id': class_id,
                    'class_name': class_info['name'],
                    'curricula': curriculum_info
                })
                
                # マイルストーン追跡
                milestones = Milestone.query.filter_by(class_id=class_id).all()
                milestone_data = []
                for milestone in milestones:
                    milestone_data.append({
                        'id': milestone.id,
                        'title': milestone.title,
                        'due_date': milestone.due_date.isoformat() if milestone.due_date else None,
                        'status': self._determine_milestone_status(milestone),
                        'completion_rate': self._calculate_milestone_completion_rate(milestone.id, class_id)
                    })
                
                management_data['milestone_tracking'].append({
                    'class_id': class_id,
                    'class_name': class_info['name'],
                    'milestones': milestone_data
                })
            
            return management_data
            
        except Exception as e:
            logger.error(f"Error getting class management data: {str(e)}")
            return {'curriculum_management': [], 'milestone_tracking': []}

    def generate_teacher_alerts(self, teacher_id: int, teacher_classes: List[Dict]) -> List[Dict]:
        """
        教師向けアラート・通知生成
        
        Args:
            teacher_id: 教師ID
            teacher_classes: 教師のクラス一覧
            
        Returns:
            List[Dict]: アラート一覧
        """
        try:
            logger.info(f"Generating teacher alerts for teacher {teacher_id}")
            
            alerts = []
            
            for class_info in teacher_classes:
                class_id = class_info['id']
                
                # 進捗遅れの学生
                struggling_students = self._identify_struggling_students(class_id)
                if struggling_students:
                    alerts.append({
                        'type': 'student_progress',
                        'severity': 'warning',
                        'title': f'進捗遅れの学生 ({class_info["name"]})',
                        'message': f'{len(struggling_students)}名の学生が進捗遅れています',
                        'data': struggling_students,
                        'action_required': True
                    })
                
                # 期限間近のマイルストーン
                upcoming_milestones = self._get_upcoming_milestones(class_id)
                if upcoming_milestones:
                    alerts.append({
                        'type': 'milestone',
                        'severity': 'info',
                        'title': f'期限間近のマイルストーン ({class_info["name"]})',
                        'message': f'{len(upcoming_milestones)}個のマイルストーンが期限間近です',
                        'data': upcoming_milestones,
                        'action_required': False
                    })
                
                # 未読チャット
                unread_chats = self._count_unread_chats(teacher_id, class_id)
                if unread_chats > 0:
                    alerts.append({
                        'type': 'communication',
                        'severity': 'info',
                        'title': f'未読チャット ({class_info["name"]})',
                        'message': f'{unread_chats}件の未読チャットがあります',
                        'data': {'unread_count': unread_chats},
                        'action_required': False
                    })
            
            # 重要度順にソート
            alerts.sort(key=lambda x: {'error': 3, 'warning': 2, 'info': 1}.get(x['severity'], 0), reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating teacher alerts: {str(e)}")
            return []

    def _integrate_phase8d_analytics(self, teacher_id: int, teacher_classes: List[Dict]) -> Dict[str, Any]:
        """Phase8D分析サービスとの統合"""
        try:
            class_ids = [cls['id'] for cls in teacher_classes]
            
            integrated_data = {
                'activity_analytics': {},
                'basebuilder_statistics': {},
                'learning_trends': {}
            }
            
            # Phase8D活動分析サービス統合
            for class_id in class_ids:
                try:
                    activity_data = self.activity_analytics_service.generate_class_activity_report(class_id)
                    integrated_data['activity_analytics'][class_id] = activity_data
                except Exception as e:
                    logger.warning(f"Activity analytics error for class {class_id}: {str(e)}")
            
            # Phase8D BaseBuilder統合
            try:
                basebuilder_summary = self.basebuilder_service.generate_teacher_basebuilder_summary(
                    teacher_id, class_ids
                )
                integrated_data['basebuilder_statistics'] = basebuilder_summary
            except Exception as e:
                logger.warning(f"BaseBuilder integration error: {str(e)}")
            
            return integrated_data
            
        except Exception as e:
            logger.error(f"Error integrating Phase8D analytics: {str(e)}")
            return {'activity_analytics': {}, 'basebuilder_statistics': {}}

    def _get_teacher_classes(self, teacher_id: int) -> List[Dict]:
        """教師のクラス一覧取得"""
        try:
            classes = Class.query.filter_by(teacher_id=teacher_id).all()
            return [{'id': cls.id, 'name': cls.name, 'description': cls.description} for cls in classes]
        except Exception:
            return []

    def _generate_class_statistics(self, class_id: int) -> Dict[str, Any]:
        """クラス別統計生成"""
        try:
            student_count = ClassEnrollment.query.filter_by(class_id=class_id).count()
            curriculum_count = Curriculum.query.filter_by(class_id=class_id).count()
            
            return {
                'student_count': student_count,
                'curriculum_count': curriculum_count,
                'activity_level': self._calculate_class_activity_level(class_id)
            }
        except Exception:
            return {'student_count': 0, 'curriculum_count': 0, 'activity_level': 0}

    def _calculate_teacher_performance_metrics(self, teacher_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """教師パフォーマンス指標計算"""
        try:
            # 簡易実装
            return {
                'student_engagement': 85.0,
                'curriculum_completion_rate': 78.5,
                'response_time': 2.3,
                'satisfaction_score': 4.2
            }
        except Exception:
            return {}

    def _analyze_teaching_trends(self, teacher_id: int, class_ids: List[int]) -> Dict[str, Any]:
        """教学トレンド分析"""
        try:
            # 簡易実装
            return {
                'weekly_trend': 'improving',
                'monthly_trend': 'stable',
                'key_improvements': ['student_engagement', 'response_time']
            }
        except Exception:
            return {}

    def _get_students_in_class(self, class_id: int) -> List[Dict]:
        """クラス内学生取得"""
        try:
            enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
            students = []
            for enrollment in enrollments:
                user = User.query.get(enrollment.student_id)
                if user:
                    students.append({'id': user.id, 'name': user.username})
            return students
        except Exception:
            return []

    def _analyze_progress_patterns(self, progress_summary: List[Dict]) -> Dict[str, Any]:
        """進捗パターン分析"""
        try:
            # 簡易実装
            return {
                'overall_trend': 'positive',
                'risk_students': 3,
                'high_performers': 12
            }
        except Exception:
            return {}

    def _generate_improvement_suggestions(self, analysis_results: Dict) -> List[str]:
        """改善提案生成"""
        try:
            suggestions = []
            if analysis_results.get('risk_students', 0) > 0:
                suggestions.append('進捗遅れの学生に個別サポートを提供してください')
            return suggestions
        except Exception:
            return []

    def _determine_curriculum_status(self, curriculum) -> str:
        """カリキュラム状態判定"""
        return 'active'  # 簡易実装

    def _calculate_curriculum_completion_rate(self, curriculum_id: int) -> float:
        """カリキュラム完了率計算"""
        return 75.0  # 簡易実装

    def _determine_milestone_status(self, milestone) -> str:
        """マイルストーン状態判定"""
        return 'in_progress'  # 簡易実装

    def _calculate_milestone_completion_rate(self, milestone_id: int, class_id: int) -> float:
        """マイルストーン完了率計算"""
        return 60.0  # 簡易実装

    def _identify_struggling_students(self, class_id: int) -> List[Dict]:
        """進捗遅れ学生特定"""
        return []  # 簡易実装

    def _get_upcoming_milestones(self, class_id: int) -> List[Dict]:
        """期限間近マイルストーン取得"""
        try:
            upcoming = Milestone.query.filter_by(class_id=class_id).filter(
                Milestone.due_date >= datetime.now(),
                Milestone.due_date <= datetime.now() + timedelta(days=7)
            ).all()
            
            return [{'id': m.id, 'title': m.title, 'due_date': m.due_date.isoformat()} for m in upcoming]
        except Exception:
            return []

    def _count_unread_chats(self, teacher_id: int, class_id: int) -> int:
        """未読チャット数カウント"""
        try:
            return ChatHistory.query.filter_by(class_id=class_id).filter(
                ChatHistory.created_at >= datetime.now() - timedelta(days=1)
            ).count()
        except Exception:
            return 0

    def _calculate_class_activity_level(self, class_id: int) -> float:
        """クラス活動レベル計算"""
        return 85.0  # 簡易実装

    def _get_empty_dashboard_data(self) -> Dict[str, Any]:
        """空のダッシュボードデータ"""
        return {
            'teacher_info': {'teacher_id': 0, 'classes': [], 'total_students': 0},
            'teacher_statistics': {'basic_stats': {}, 'class_statistics': []},
            'student_progress_analysis': {'progress_summary': [], 'analysis_results': {}},
            'class_management_data': {'curriculum_management': [], 'milestone_tracking': []},
            'teacher_alerts': [],
            'integrated_analytics': {'activity_analytics': {}, 'basebuilder_statistics': {}},
            'generated_at': datetime.now().isoformat()
        }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            'service_name': 'TeacherDashboardService',
            'status': 'active',
            'version': '1.0.0',
            'phase8d_integration': True,
            'integrated_services': [
                'DashboardOrchestrationService',
                'LearningProgressService',
                'ActivityAnalyticsService',
                'BaseBuilderIntegrationService',
                'StudentDashboardDataService'
            ],
            'capabilities': [
                'teacher_statistics_generation',
                'student_progress_analysis',
                'class_management_data',
                'teacher_alerts_generation',
                'phase8d_analytics_integration'
            ]
        }