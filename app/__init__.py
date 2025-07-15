# app/__init__.py
import logging
import logging.handlers
import os

from flask import Flask, abort, make_response, redirect, send_from_directory, url_for
from flask_login import current_user, login_required

from config import get_config
from extensions import admin, csrf, db, limiter, login_manager, migrate

# Flask-Admin関連のインポートを条件付きに
if admin:
    from flask_admin import AdminIndexView
    from flask_admin.contrib.sqla import ModelView

    class AdminModelView(ModelView):
        """管理画面のカスタムビュー"""

        def is_accessible(self):
            return current_user.is_authenticated and current_user.role == "teacher"

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for("auth.login"))

    class CustomAdminIndexView(AdminIndexView):
        """管理画面のインデックスビュー"""

        def is_accessible(self):
            return current_user.is_authenticated and current_user.role == "teacher"

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for("auth.login"))

else:
    AdminModelView = None
    CustomAdminIndexView = None


def create_app(config_object=None):
    """アプリケーションファクトリー"""
    # テンプレートフォルダを親ディレクトリに設定
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # 設定を読み込む
    config = config_object or get_config()
    app.config.from_object(config)

    # アップロードフォルダの作成
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # 拡張機能を初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "この機能を使用するにはログインしてください。"

    # 管理画面を初期化
    if admin:
        admin.init_app(app)

    csrf.init_app(app)
    limiter.init_app(app)

    # SocketIOを初期化（リアルタイム同期用）
    from app.realtime import init_socketio

    socketio = init_socketio(app)
    app.socketio = socketio

    # Celeryを初期化（利用可能な場合のみ）
    from app.tasks import CELERY_AVAILABLE, make_celery

    if CELERY_AVAILABLE:
        celery = make_celery(app)
        app.celery = celery

    # テンプレートフィルターを登録
    register_template_filters(app)

    # バージョン管理を初期化
    from app.version import init_version

    init_version(app)

    with app.app_context():
        # モデルをインポート
        from app.models import (
            ActivityLog,
            ChatHistory,
            Class,
            ClassEnrollment,
            ClassGroup,
            Curriculum,
            Goal,
            Group,
            GroupMembership,
            InquiryTheme,
            InterestSurvey,
            MainTheme,
            Milestone,
            PersonalitySurvey,
            RubricTemplate,
            School,
            SchoolYear,
            StudentEnrollment,
            StudentEvaluation,
            Todo,
            User,
        )

        # ユーザーローダーを設定
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        # 管理画面にモデルを登録
        register_admin_views()

        # Blueprintを登録
        register_blueprints(app)

        # 特殊なルートを登録
        from app.special_routes import register_special_routes

        register_special_routes(app)

        # BaseBuilderモジュールを初期化（堅牢化）
        try:
            from basebuilder import init_app as init_basebuilder

            init_basebuilder(app)
            app.config["BASEBUILDER_AVAILABLE"] = True
            app.logger.info("[SUCCESS] BaseBuilder module initialized successfully")
        except ImportError as e:
            app.config["BASEBUILDER_AVAILABLE"] = False
            app.logger.error(
                f"[ERROR] Failed to initialize BaseBuilder (ImportError): {e}"
            )
            import traceback

            app.logger.error(traceback.format_exc())
        except Exception as e:
            app.config["BASEBUILDER_AVAILABLE"] = False
            app.logger.error(
                f"[ERROR] Failed to initialize BaseBuilder (General Error): {e}"
            )
            import traceback

            app.logger.error(traceback.format_exc())

        # シェルコンテキストプロセッサを登録
        register_shell_context(app)

        # エラーハンドリングとセキュリティ機能を設定
        setup_error_handling_and_security(app)

        # ヘルスチェックエンドポイントを登録
        from app.utils.health_check import create_health_endpoint

        create_health_endpoint(app)

    return app


def register_template_filters(app):
    """テンプレートフィルターを登録"""
    import json

    @app.template_filter("nl2br")
    def nl2br(value):
        """改行をHTMLのbrタグに変換するフィルター（XSS対策付き）"""
        if not value:
            return value

        # bleachでサニタイズ（HTMLタグを除去）
        import bleach
        import markupsafe

        # 許可するタグを制限（brタグのみ）
        allowed_tags = ["br"]
        cleaned = bleach.clean(str(value), tags=allowed_tags, strip=True)

        # エスケープしてから改行を<br>に変換
        escaped = markupsafe.escape(cleaned)
        return markupsafe.Markup(str(escaped).replace("\n", "<br>\n"))

    @app.template_filter("fromjson")
    def fromjson_filter(value):
        """JSON文字列をPythonオブジェクトに変換するフィルター"""
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}


def register_admin_views():
    """管理画面にモデルビューを登録"""
    if not admin or not AdminModelView:
        return

    from app.models import (
        ActivityLog,
        ChatHistory,
        Class,
        ClassEnrollment,
        ClassGroup,
        Curriculum,
        Goal,
        Group,
        GroupMembership,
        InquiryTheme,
        InterestSurvey,
        MainTheme,
        Milestone,
        PersonalitySurvey,
        RubricTemplate,
        School,
        SchoolYear,
        StudentEnrollment,
        StudentEvaluation,
        Todo,
        User,
        db,
    )

    # モデルを管理画面に登録
    admin.add_view(AdminModelView(User, db.session, name="ユーザー"))
    admin.add_view(AdminModelView(School, db.session, name="学校"))
    admin.add_view(AdminModelView(SchoolYear, db.session, name="学校年度"))
    admin.add_view(AdminModelView(ClassGroup, db.session, name="クラスグループ"))
    admin.add_view(AdminModelView(StudentEnrollment, db.session, name="生徒登録"))
    admin.add_view(AdminModelView(Class, db.session, name="クラス"))
    admin.add_view(AdminModelView(ClassEnrollment, db.session, name="クラス履修"))
    admin.add_view(AdminModelView(MainTheme, db.session, name="メインテーマ"))
    admin.add_view(AdminModelView(InquiryTheme, db.session, name="探究テーマ"))
    admin.add_view(AdminModelView(InterestSurvey, db.session, name="興味関心調査"))
    admin.add_view(AdminModelView(PersonalitySurvey, db.session, name="性格調査"))
    admin.add_view(AdminModelView(ActivityLog, db.session, name="活動記録"))
    admin.add_view(AdminModelView(Todo, db.session, name="To Do"))
    admin.add_view(AdminModelView(Goal, db.session, name="目標"))
    admin.add_view(AdminModelView(StudentEvaluation, db.session, name="生徒評価"))
    admin.add_view(AdminModelView(Curriculum, db.session, name="カリキュラム"))
    admin.add_view(AdminModelView(RubricTemplate, db.session, name="ルーブリック"))
    admin.add_view(AdminModelView(Group, db.session, name="グループ"))
    admin.add_view(AdminModelView(GroupMembership, db.session, name="グループメンバー"))
    admin.add_view(AdminModelView(ChatHistory, db.session, name="チャット履歴"))
    admin.add_view(AdminModelView(Milestone, db.session, name="マイルストーン"))


def register_blueprints(app):
    """Blueprintを登録"""
    from app.admin import admin_bp
    from app.api import register_api_routes
    from app.auth import auth_bp
    from app.realtime import realtime_bp
    from app.student import student_bp
    from app.teacher import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    register_api_routes(app)  # モジュラーAPI構造を登録
    app.register_blueprint(realtime_bp)

    # モジュール化されたBlueprintを登録
    from app.student import register_student_blueprints
    from app.teacher import register_teacher_blueprints

    register_teacher_blueprints(app)
    register_student_blueprints(app)
    
    # 新しいモジュールシステムを登録
    try:
        from app.modules import MODULAR_BLUEPRINTS
        for blueprint in MODULAR_BLUEPRINTS:
            app.register_blueprint(blueprint)
        app.logger.info("[SUCCESS] Modular blueprints registered successfully")
    except ImportError as e:
        app.logger.warning(f"[WARNING] Modular blueprints not available: {e}")
    except Exception as e:
        app.logger.error(f"[ERROR] Failed to register modular blueprints: {e}")

    # ルートURLのハンドラー
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin_panel.dashboard"))
            elif current_user.role == "teacher":
                return redirect(url_for("teacher_dashboard.dashboard"))
            elif current_user.role == "student":
                return redirect(url_for("student_dashboard.dashboard"))
        return redirect(url_for("auth.login"))


def register_shell_context(app):
    """シェルコンテキストプロセッサを登録"""

    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
            ActivityLog,
            ChatHistory,
            Class,
            ClassEnrollment,
            ClassGroup,
            Curriculum,
            Goal,
            Group,
            GroupMembership,
            InquiryTheme,
            InterestSurvey,
            MainTheme,
            Milestone,
            PersonalitySurvey,
            RubricTemplate,
            School,
            SchoolYear,
            StudentEnrollment,
            StudentEvaluation,
            Todo,
            User,
            db,
        )

        return {
            "db": db,
            "User": User,
            "School": School,
            "SchoolYear": SchoolYear,
            "ClassGroup": ClassGroup,
            "StudentEnrollment": StudentEnrollment,
            "Class": Class,
            "ClassEnrollment": ClassEnrollment,
            "MainTheme": MainTheme,
            "InquiryTheme": InquiryTheme,
            "InterestSurvey": InterestSurvey,
            "PersonalitySurvey": PersonalitySurvey,
            "ActivityLog": ActivityLog,
            "Todo": Todo,
            "Goal": Goal,
            "StudentEvaluation": StudentEvaluation,
            "Curriculum": Curriculum,
            "RubricTemplate": RubricTemplate,
            "Group": Group,
            "GroupMembership": GroupMembership,
            "ChatHistory": ChatHistory,
            "Milestone": Milestone,
        }


def setup_error_handling_and_security(app):
    """
    エラーハンドリングとセキュリティ機能を設定

    この関数は、アプリケーション全体のセキュリティとエラーハンドリングを
    統一的に設定し、本番環境での安全性を確保します。
    """
    # ログ設定の初期化
    setup_logging(app)

    # エラーハンドラーの設定
    from app.utils.error_handler import setup_error_handlers

    setup_error_handlers(app)

    # セキュリティヘッダーの設定
    from app.utils.security import setup_security_headers

    setup_security_headers(app)

    # データベースセキュリティの設定
    from app.utils.database_security import setup_database_security

    setup_database_security(app)

    # APIセキュリティの設定
    from app.utils.api_security import setup_api_security

    setup_api_security(app)

    # リクエストコンテキストロガーの設定
    from app.utils.error_handler import RequestContextLogger

    @app.before_request
    def log_request_start():
        """各リクエスト開始時のログ記録"""
        RequestContextLogger.log_request_start()

    @app.after_request
    def log_request_end(response):
        """各リクエスト終了時のログ記録"""
        return RequestContextLogger.log_request_end(response)

    logging.info("エラーハンドリングとセキュリティ機能を初期化しました")


def setup_logging(app):
    """
    ログ設定の初期化

    開発環境と本番環境で適切なログレベルとフォーマットを設定します。
    セキュリティイベントと通常のアプリケーションログを分離して記録します。
    """
    if not app.debug and not app.testing:
        # 本番環境でのログ設定
        if not os.path.exists("logs"):
            os.mkdir("logs")

        # メインアプリケーションログ
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/questeD.log", maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        # セキュリティイベント専用ログ
        security_handler = logging.handlers.RotatingFileHandler(
            "logs/security.log", maxBytes=10240000, backupCount=10
        )
        security_handler.setFormatter(
            logging.Formatter("%(asctime)s SECURITY: %(message)s")
        )
        security_handler.setLevel(logging.WARNING)

        # セキュリティロガーの設定
        security_logger = logging.getLogger("security")
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.WARNING)

        app.logger.setLevel(logging.INFO)
        app.logger.info("QuestEdアプリケーションが起動しました")
    else:
        # 開発環境でのログ設定
        app.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
