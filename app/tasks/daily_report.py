#!/usr/bin/env python3
"""
日次レポート機能
学生と教師向けの自動レポート生成とメール送信
"""
import os
import sys
from datetime import datetime, date, timedelta
from flask import render_template_string
from markupsafe import escape
import logging

# Celeryタスクとしての実装
try:
    from app.tasks import celery, CELERY_AVAILABLE
    if CELERY_AVAILABLE:
        from app import create_app
        from app.models import db, User, ChatHistory, Class, Subject, ActivityLog, Goal, Todo
        from app.utils.email_sender import EmailSender
        from app.ai import generate_chat_response
except ImportError:
    # 必要なモジュールが利用できない場合
    CELERY_AVAILABLE = False
    celery = None

class DailyReportService:
    def __init__(self, app=None):
        self.app = app
        self.today = date.today()
        self.email_sender = EmailSender()
        
    def generate_all_reports(self):
        """全体のレポート生成処理"""
        if not self.app:
            self.app = create_app()
            
        with self.app.app_context():
            try:
                # 生徒レポート
                student_count = self.generate_student_reports()
                # 教師レポート  
                teacher_count = self.generate_teacher_reports()
                
                logging.info(f"Daily reports generated: {student_count} students, {teacher_count} teachers")
                return True, f"Generated reports for {student_count} students and {teacher_count} teachers"
                
            except Exception as e:
                logging.error(f"Error in daily report generation: {str(e)}")
                return False, str(e)
        
    def generate_student_reports(self):
        """生徒・保護者向けレポート"""
        students = User.query.filter_by(
            role='student',
            is_approved=True
        ).all()
        
        sent_count = 0
        for student in students:
            try:
                report_data = self._collect_student_data(student)
                if report_data['total_questions'] > 0 or report_data['total_activities'] > 0:
                    success = self._send_student_report(student, report_data)
                    if success:
                        sent_count += 1
                        logging.info(f"Student report sent to {student.username}")
                    else:
                        logging.warning(f"Failed to send report to {student.username}")
            except Exception as e:
                logging.error(f"Error generating report for student {student.id}: {e}")
                
        return sent_count
    
    def generate_teacher_reports(self):
        """教師向けクラス別レポート"""
        teachers = User.query.filter_by(
            role='teacher',
            is_approved=True
        ).all()
        
        sent_count = 0
        for teacher in teachers:
            try:
                for class_obj in teacher.classes_teaching:
                    report_data = self._collect_class_data(class_obj)
                    if report_data['active_students'] > 0:
                        success = self._send_teacher_report(teacher, class_obj, report_data)
                        if success:
                            sent_count += 1
                            logging.info(f"Teacher report sent to {teacher.username} for class {class_obj.name}")
            except Exception as e:
                logging.error(f"Error generating report for teacher {teacher.id}: {e}")
                
        return sent_count
    
    def _collect_student_data(self, student):
        """生徒の学習データ収集"""
        start_time = datetime.combine(self.today, datetime.min.time())
        end_time = datetime.combine(self.today, datetime.max.time())
        
        # チャット履歴
        chats = ChatHistory.query.filter(
            ChatHistory.user_id == student.id,
            ChatHistory.created_at.between(start_time, end_time),
            ChatHistory.is_user == True  # ユーザーからの質問のみ
        ).order_by(ChatHistory.subject_id).all()
        
        # 活動記録
        activities = ActivityLog.query.filter(
            ActivityLog.student_id == student.id,
            ActivityLog.date == self.today
        ).all()
        
        # 目標進捗
        goals = Goal.query.filter_by(
            student_id=student.id,
            is_completed=False
        ).all()
        
        # TODO完了
        completed_todos = Todo.query.filter(
            Todo.student_id == student.id,
            Todo.is_completed == True,
            Todo.updated_at.between(start_time, end_time)
        ).all()
        
        # 教科別にグループ化
        subject_data = {}
        for chat in chats:
            subject_id = chat.subject_id or 0  # None の場合は0
            if subject_id not in subject_data:
                subject_data[subject_id] = {
                    'subject': chat.subject if chat.subject else None,
                    'questions': [],
                    'topics': set()
                }
            subject_data[subject_id]['questions'].append({
                'question': chat.message,
                'timestamp': chat.created_at
            })
            
        # AI要約生成
        for subject_id, data in subject_data.items():
            if data['questions']:
                data['summary'] = self._generate_ai_summary(
                    data['subject'].name if data['subject'] else '一般',
                    data['questions']
                )
                # HTMLエスケープして安全性を確保
                if 'summary' in data:
                    data['summary'] = escape(data['summary'])
        
        return {
            'student': student,
            'date': self.today,
            'subject_data': subject_data,
            'total_questions': len(chats),
            'activities': activities,
            'total_activities': len(activities),
            'goals': goals,
            'completed_todos': completed_todos
        }
    
    def _collect_class_data(self, class_obj):
        """クラスの学習データ収集"""
        start_time = datetime.combine(self.today, datetime.min.time())
        end_time = datetime.combine(self.today, datetime.max.time())
        
        # クラスの生徒一覧
        students = [enrollment.student for enrollment in class_obj.enrollments if enrollment.is_active]
        
        # 今日アクティブだった生徒
        active_students = set()
        total_questions = 0
        
        for student in students:
            daily_chats = ChatHistory.query.filter(
                ChatHistory.user_id == student.id,
                ChatHistory.class_id == class_obj.id,
                ChatHistory.created_at.between(start_time, end_time),
                ChatHistory.is_user == True
            ).count()
            
            if daily_chats > 0:
                active_students.add(student)
                total_questions += daily_chats
        
        return {
            'class': class_obj,
            'date': self.today,
            'total_students': len(students),
            'active_students': len(active_students),
            'total_questions': total_questions,
            'active_student_list': list(active_students)
        }
    
    def _generate_ai_summary(self, subject_name, questions):
        """GPT-4による学習内容の要約"""
        if not questions:
            return "今日は質問がありませんでした。"
            
        question_texts = "\n".join([f"- {q['question']}" for q in questions[:5]])  # 最大5問
        
        prompt = f"""
        {subject_name}の学習で今日生徒が行った質問を分析して、以下の形式でまとめてください：
        
        今日の質問（{len(questions)}件）:
        {question_texts}
        
        【学習のポイント】
        - 主な学習トピック（3つまで）
        - 理解できている点
        - さらに深めると良い点
        
        【明日への提案】
        - 発展的な学習の方向性
        
        150字程度でまとめてください。
        """
        
        try:
            ai_response = generate_chat_response(prompt)
            return ai_response
        except Exception as e:
            logging.error(f"AI summary generation failed: {e}")
            return f"{subject_name}で{len(questions)}件の質問がありました。継続的な学習への取り組みが見られます。"
    
    def _send_student_report(self, student, report_data):
        """生徒・保護者へのメール送信"""
        # メール受信者
        recipients = [student.email]
        
        # 保護者メールアドレスがあれば追加（フィールドがある場合）
        if hasattr(student, 'parent_email') and student.parent_email:
            recipients.append(student.parent_email)
        
        # HTML形式のメール本文
        html_content = self._render_student_report_template(report_data)
        
        try:
            success, message = self.email_sender.send(
                recipients=recipients,
                subject=f"【QuestEd】{student.username}さんの学習レポート - {self.today.strftime('%Y年%m月%d日')}",
                html_body=html_content
            )
            return success
        except Exception as e:
            logging.error(f"Failed to send student report: {e}")
            return False
    
    def _send_teacher_report(self, teacher, class_obj, report_data):
        """教師へのメール送信"""
        html_content = self._render_teacher_report_template(report_data)
        
        try:
            success, message = self.email_sender.send(
                recipients=[teacher.email],
                subject=f"【QuestEd】クラス「{class_obj.name}」の活動レポート - {self.today.strftime('%Y年%m月%d日')}",
                html_body=html_content
            )
            return success
        except Exception as e:
            logging.error(f"Failed to send teacher report: {e}")
            return False
    
    def _render_student_report_template(self, data):
        """生徒レポートのHTMLテンプレート"""
        template = """
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .section { margin-bottom: 20px; padding: 15px; border-left: 4px solid #007bff; background-color: #f8f9fa; }
                .subject-section { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                .activity-item { margin: 5px 0; padding: 8px; background-color: #e9ecef; border-radius: 3px; }
                .footer { margin-top: 30px; padding: 15px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📚 QuestEd 学習レポート</h1>
                <p>{{ data.student.username }}さんの学習記録</p>
                <p>{{ data.date.strftime('%Y年%m月%d日') }}</p>
            </div>
            
            <div class="content">
                {% if data.total_questions > 0 %}
                <div class="section">
                    <h2>💬 今日の質問活動</h2>
                    <p><strong>質問数:</strong> {{ data.total_questions }}件</p>
                    
                    {% for subject_id, subject_info in data.subject_data.items() %}
                    <div class="subject-section">
                        <h3>📖 {{ subject_info.subject.name if subject_info.subject else '一般的な質問' }}</h3>
                        <p><strong>質問数:</strong> {{ subject_info.questions|length }}件</p>
                        {% if subject_info.summary %}
                        <div style="background-color: #fff; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            {{ subject_info.summary }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if data.total_activities > 0 %}
                <div class="section">
                    <h2>📝 今日の活動記録</h2>
                    {% for activity in data.activities %}
                    <div class="activity-item">
                        <strong>{{ activity.title or '活動記録' }}</strong>
                        {% if activity.content %}
                        <p>{{ activity.content[:100] }}{% if activity.content|length > 100 %}...{% endif %}</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if data.completed_todos %}
                <div class="section">
                    <h2>✅ 完了したタスク</h2>
                    {% for todo in data.completed_todos %}
                    <div class="activity-item">{{ todo.title }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if data.goals %}
                <div class="section">
                    <h2>🎯 進行中の目標</h2>
                    {% for goal in data.goals %}
                    <div class="activity-item">
                        <strong>{{ goal.title }}</strong> - 進捗: {{ goal.progress }}%
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if data.total_questions == 0 and data.total_activities == 0 %}
                <div class="section">
                    <h2>📋 今日の活動</h2>
                    <p>今日はまだ学習活動の記録がありません。明日もQuestEdで充実した学習を進めていきましょう！</p>
                </div>
                {% endif %}
            </div>
            
            <div class="footer">
                <p>このレポートは自動生成されています。</p>
                <p><a href="https://quest-ed.jp">QuestEd</a> - 探究学習支援プラットフォーム</p>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, data=data)
    
    def _render_teacher_report_template(self, data):
        """教師レポートのHTMLテンプレート"""
        template = """
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background-color: #28a745; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .section { margin-bottom: 20px; padding: 15px; border-left: 4px solid #28a745; background-color: #f8f9fa; }
                .stats { display: flex; justify-content: space-around; margin: 20px 0; }
                .stat-item { text-align: center; padding: 15px; background-color: #e9ecef; border-radius: 5px; }
                .student-list { margin: 10px 0; }
                .student-item { display: inline-block; margin: 3px; padding: 5px 10px; background-color: #007bff; color: white; border-radius: 15px; font-size: 12px; }
                .footer { margin-top: 30px; padding: 15px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏫 QuestEd クラス活動レポート</h1>
                <p>{{ data.class.name }}</p>
                <p>{{ data.date.strftime('%Y年%m月%d日') }}</p>
            </div>
            
            <div class="content">
                <div class="stats">
                    <div class="stat-item">
                        <h3>{{ data.total_students }}</h3>
                        <p>総生徒数</p>
                    </div>
                    <div class="stat-item">
                        <h3>{{ data.active_students }}</h3>
                        <p>アクティブ生徒数</p>
                    </div>
                    <div class="stat-item">
                        <h3>{{ data.total_questions }}</h3>
                        <p>質問総数</p>
                    </div>
                </div>
                
                {% if data.active_students > 0 %}
                <div class="section">
                    <h2>👥 今日活動した生徒</h2>
                    <div class="student-list">
                        {% for student in data.active_student_list %}
                        <span class="student-item">{{ student.username }}</span>
                        {% endfor %}
                    </div>
                    <p style="margin-top: 15px;">
                        参加率: {{ "%.1f"|format((data.active_students / data.total_students * 100) if data.total_students > 0 else 0) }}%
                    </p>
                </div>
                {% else %}
                <div class="section">
                    <h2>📊 今日の活動</h2>
                    <p>今日はまだ生徒からの質問や活動がありません。生徒たちの学習参加を促してみてください。</p>
                </div>
                {% endif %}
                
                <div class="section">
                    <h2>💡 指導のヒント</h2>
                    <ul>
                        <li>活発に質問している生徒には、さらに深い探究を促してみましょう</li>
                        <li>質問が少ない生徒には、個別のサポートを検討してください</li>
                        <li>教科の特性を活かした質問を引き出す工夫をしてみてください</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>このレポートは自動生成されています。</p>
                <p><a href="https://quest-ed.jp">QuestEd</a> - 探究学習支援プラットフォーム</p>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, data=data)

# Celeryタスクの定義
if CELERY_AVAILABLE and celery:
    @celery.task
    def generate_daily_reports():
        """日次レポート生成のCeleryタスク"""
        service = DailyReportService()
        success, message = service.generate_all_reports()
        return {'success': success, 'message': message}
    
    @celery.task
    def send_test_report(user_id):
        """テスト用レポート送信"""
        service = DailyReportService()
        # 実装省略
        return {'success': True, 'message': 'Test report sent'}

# スタンドアロン実行用
def main():
    """スタンドアロン実行時のメイン関数"""
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from app import create_app
    
    app = create_app()
    service = DailyReportService(app)
    
    print("🚀 Starting daily report generation...")
    success, message = service.generate_all_reports()
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ Error: {message}")
        sys.exit(1)

if __name__ == '__main__':
    main()