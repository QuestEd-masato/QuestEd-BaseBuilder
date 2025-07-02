"""
BaseBuilder Services Layer
ビジネスロジックを分離し、ルートハンドラーをシンプル化
"""

from datetime import datetime, date
from extensions import db
from basebuilder.models import *


class ProficiencyService:
    """習熟度管理サービス"""
    
    @staticmethod
    def calculate_proficiency(student_id, category_id=None):
        """習熟度計算"""
        query = AnswerRecord.query.filter_by(student_id=student_id)
        if category_id:
            query = query.join(BasicKnowledgeItem).filter(
                BasicKnowledgeItem.category_id == category_id
            )
        
        records = query.all()
        if not records:
            return 0
        
        correct_count = sum(1 for r in records if r.is_correct)
        total_count = len(records)
        
        return round((correct_count / total_count) * 100, 1)
    
    @staticmethod
    def update_proficiency_record(student_id, category_id, proficiency_level):
        """習熟度記録の更新"""
        record = ProficiencyRecord.query.filter_by(
            student_id=student_id,
            category_id=category_id
        ).first()
        
        if record:
            record.proficiency_level = proficiency_level
            record.updated_at = datetime.now()
        else:
            record = ProficiencyRecord(
                student_id=student_id,
                category_id=category_id,
                proficiency_level=proficiency_level,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(record)
        
        db.session.commit()
        return record


class SessionService:
    """学習セッション管理サービス"""
    
    @staticmethod
    def create_answer_record(student_id, problem_id, is_correct, response_time=None):
        """回答記録の作成"""
        record = AnswerRecord(
            student_id=student_id,
            problem_id=problem_id,
            is_correct=is_correct,
            response_time=response_time,
            created_at=datetime.now()
        )
        
        db.session.add(record)
        db.session.commit()
        
        # 習熟度の自動更新
        problem = BasicKnowledgeItem.query.get(problem_id)
        if problem:
            proficiency = ProficiencyService.calculate_proficiency(
                student_id, problem.category_id
            )
            ProficiencyService.update_proficiency_record(
                student_id, problem.category_id, proficiency
            )
        
        return record


class DashboardService:
    """ダッシュボードデータ管理サービス"""
    
    @staticmethod
    def get_student_dashboard_data(user):
        """学生ダッシュボードデータの取得"""
        enrolled_class_ids = [c.id for c in user.enrolled_classes]
        
        # 配信テキスト取得
        delivered_texts = TextDelivery.query.filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).order_by(TextDelivery.delivered_at.desc()).limit(5).all()
        
        # カテゴリごとのテキスト分類
        categories_with_texts = {}
        for delivery in delivered_texts:
            category = delivery.text_set.category
            if category.id not in categories_with_texts:
                categories_with_texts[category.id] = {
                    'category': category,
                    'texts': []
                }
            categories_with_texts[category.id]['texts'].append(delivery)
        
        # 習熟度記録
        proficiency_records = ProficiencyRecord.query.filter_by(
            student_id=user.id
        ).all()
        
        # 最近の回答記録
        recent_answers = AnswerRecord.query.filter_by(
            student_id=user.id
        ).order_by(AnswerRecord.created_at.desc()).limit(10).all()
        
        return {
            'categories_with_texts': categories_with_texts,
            'proficiency_records': proficiency_records,
            'recent_answers': recent_answers
        }
    
    @staticmethod
    def get_teacher_dashboard_data(user):
        """教師ダッシュボードデータの取得"""
        teacher_classes = user.classes
        
        # クラス統計
        class_stats = {}
        for class_obj in teacher_classes:
            student_count = len(class_obj.enrolled_students)
            delivered_text_count = TextDelivery.query.filter_by(
                class_id=class_obj.id
            ).count()
            
            class_stats[class_obj.id] = {
                'student_count': student_count,
                'delivered_text_count': delivered_text_count
            }
        
        # カテゴリ・テキストセット一覧
        categories = ProblemCategory.query.order_by(ProblemCategory.name).all()
        text_sets = TextSet.query.order_by(TextSet.created_at.desc()).limit(10).all()
        
        return {
            'teacher_classes': teacher_classes,
            'class_stats': class_stats,
            'categories': categories,
            'text_sets': text_sets
        }
    
    @staticmethod
    def get_admin_dashboard_data():
        """管理者ダッシュボードデータの取得"""
        total_categories = ProblemCategory.query.count()
        total_text_sets = TextSet.query.count()
        total_students = db.session.query(
            db.func.count(db.distinct(AnswerRecord.student_id))
        ).scalar()
        
        recent_deliveries = TextDelivery.query.order_by(
            TextDelivery.delivered_at.desc()
        ).limit(10).all()
        
        return {
            'total_categories': total_categories,
            'total_text_sets': total_text_sets,
            'total_students': total_students,
            'recent_deliveries': recent_deliveries
        }


class AnalyticsService:
    """分析・統計サービス"""
    
    @staticmethod
    def get_class_performance_stats(class_id):
        """クラス成績統計"""
        from app.models import User
        
        # クラスの学生を取得
        students = User.query.join(User.enrolled_classes).filter(
            User.enrolled_classes.any(id=class_id)
        ).all()
        
        stats = []
        for student in students:
            student_stats = {
                'student': student,
                'answer_count': AnswerRecord.query.filter_by(student_id=student.id).count(),
                'accuracy': ProficiencyService.calculate_proficiency(student.id)
            }
            stats.append(student_stats)
        
        return stats
    
    @staticmethod
    def get_category_difficulty_analysis():
        """カテゴリ別難易度分析"""
        categories = ProblemCategory.query.all()
        
        analysis = []
        for category in categories:
            records = AnswerRecord.query.join(BasicKnowledgeItem).filter(
                BasicKnowledgeItem.category_id == category.id
            ).all()
            
            if records:
                correct_rate = sum(1 for r in records if r.is_correct) / len(records)
                avg_response_time = sum(r.response_time or 0 for r in records) / len(records)
                
                analysis.append({
                    'category': category,
                    'correct_rate': round(correct_rate * 100, 1),
                    'avg_response_time': round(avg_response_time, 1),
                    'total_attempts': len(records)
                })
        
        return analysis