# QuestEd System Architecture

Generated on 2025-06-28 07:02:29

## 📊 System Overview

- **Total Modules**: 204
- **API Endpoints**: 1
- **Database Models**: 11
- **Lines of Code**: 60,156

## 🏗️ Architecture Layers

### Presentation Layer
- Web UI (Flask Templates)
- REST API (Flask-RESTful)
- Static Assets (CSS, JavaScript)

### Business Logic Layer
- Services: 35 modules
- Blueprints: 1 modules
- Workflow Management

### Data Access Layer
- SQLAlchemy ORM
- Database Models: 11 models
- Migration Management

### Infrastructure Layer
- Flask Application Factory
- Configuration Management
- Extension Integration

## 📦 Module Dependencies

- **celery_worker**: app.tasks, app.tasks
- **migrate_curriculum_v2**: app.models, app.services.curriculum_service_v2, app.models, app.services.curriculum_service_v2
- **test_email_simple**: app.utils.email_sender
- **pre_deploy_check**: app.models, app.utils.file_security
- **manage_celery**: app.tasks, app.tasks.daily_report, app.tasks.daily_report, app.tasks.daily_report
- **test_routes**: app.models
- **test_models**: app.models
- **test_fixes**: app.student, app.teacher, app.models, app.student, app.teacher
- **run_tests**: app.teacher, app.student, app.api, app.services.unit_item_mapping_service, app.teacher.modules.dashboard, app.teacher.modules.class_management, app.teacher.modules.curriculum_management, app.student.modules.dashboard, app.student.modules.activities, app.student.modules.surveys, app.student.modules.goals_todos, app.teacher, app.student, app.models, app.services.unit_item_mapping_service, app.api.data_integrity
- **academic**: app.models
- **school**: app.models
- **enrollment**: app.models
- **send_daily_summary**: app.models, app.utils.email_sender
- **phase3_data_integrity**: app.models
- **routes_legacy**: app.models
- **app_simple**: app.auth, app.admin, app.teacher, app.student, app.api, app.models, app.models
- **app_fixed**: app.auth, app.admin, app.teacher, app.student, app.api, app.models
- **test_ranking**: app.models, app.services.ranking_service
- **test_base**: app.models, app.models
- **conftest_fixtures**: app.models
- **conftest**: app.models, app.utils.api_security
- **blueprint_registry**: app.utils.rate_limiting, app.auth, app.admin, app.teacher, app.student, app.api
- **special_routes**: app.models
- **admin**: app.models
- **analytics**: app.models, app.services.ranking_service
- **test_models_extended**: app.models
- **test_services**: app.services.unified_curriculum_service, app.services.unified_progress_service_v2, app.features.learning.progress_manager, app.models, app.models
- **test_utils**: app.utils.security, app.utils.input_validator, app.utils.error_handler, app.utils.database_security, app.utils.api_security
- **test_refactoring**: app.models, app.teacher.modules.curriculum_management, app.teacher, app.student.modules.goals_todos, app.student, app.services.unit_item_mapping_service, app.teacher.modules.analytics, app.student, app.student.modules.dashboard, app.student.modules.activities
- **test_user_flows**: app.models
- **test_unit_management**: app.models, app.models
- **test_security**: app.models, app.utils.security, app.utils.input_validator, app.utils.api_security, app.utils.database_security
- **api_security**: app.utils.input_validator
- **auth**: app.models
- **curriculum**: app.models
- **decorators**: app.utils.database
- **health_check**: app.services.ranking_service, app.models
- **model_helpers**: app.models, app.models, app.models, app.models
- **safe_queries**: app.models
- **error_handler**: app.utils.exceptions
- **user_management**: app.models, app.admin, app.auth.password_validator, app.utils.file_security, app.utils.email_sender, app.utils.csv_helper
- **school_management**: app.models, app.admin
- **base_service**: app.utils.exceptions
- **review_system**: app.models, app.utils.rate_limiting
- **init_subjects**: app.models, app.models.subject
- **student_tools**: app.models, app.utils.rate_limiting
- **admin_teacher**: app.models, app.utils.rate_limiting
- **chat_ai**: app.models, app.ai, app.utils.rate_limiting
- **__init___legacy**: app.models, app.ai, app.utils.rate_limiting, app.services.unit_completion_service, app.models, app.models, app.services.ranking_service, app.services.ranking_service, app.models, app.services.ai_recommender, app.services.ai_recommender, app.services.ai_recommender, app.services.weakness_analyzer, app.services.spaced_repetition, app.services.spaced_repetition, app.teacher.modules.analytics, app.services.ranking_service, app.services.ranking_service, app.services.unit_progress_manager, app.services.unit_progress_manager, app.services.unit_progress_manager, app.models, app.services.ai_recommender, app.services.spaced_repetition, app.utils.validators, app.utils.csv_helper, app.models
- **data_integrity**: app.models, app.services.unit_item_mapping_service, app.utils.decorators, app.utils.logger
- **rankings**: app.models, app.utils.rate_limiting
- **base**: app.utils.exceptions
- **unit_management**: app.models, app.services.unit_completion_service, app.utils.rate_limiting
- **secure_auth**: app.models, app.auth.password_validator, app.utils.security_enhancements, app.utils.rate_limiting, app.utils.email_sender
- **curriculum_unit_service**: app.models
- **spaced_repetition**: app.models, app.services.weakness_analyzer, app.utils.exceptions
- **unified_progress_service_v2**: app.core.base_service, app.core.data_access, app.features.learning.progress_manager
- **weakness_analyzer**: app.models, app.utils.exceptions
- **review_service**: app.models
- **auto_sync_service**: app.models, app.services.curriculum_bridge_service, app.realtime
- **speech_service**: app.models
- **ai_recommender**: app.models, app.services.pattern_analyzer, app.utils.exceptions
- **unit_item_mapping_service**: app.models, app.utils.logger
- **curriculum_service**: app.models, app.models, app.models
- **unified_curriculum_service**: app.core.base_service, app.core.data_access, app.models
- **user_service**: app.models, app.services.base_service, app.utils.exceptions, app.utils.validators, app.utils.validators
- **unified_progress_service**: app.models, app.models
- **ai_recommendation_service**: app.models, app.services.curriculum_unit_service
- **curriculum_bridge_service**: app.models
- **curriculum_service_v2**: app.models, app.utils.csv_helper
- **unit_completion_service**: app.models
- **ranking_service**: app.models, app.models, app.utils.validators, app.models, app.models
- **pattern_analyzer_example**: app.services.pattern_analyzer, app.models, app.services.pattern_analyzer
- **unit_progress_manager**: app.models
- **scheduled_sync_service**: app.models, app.services.auto_sync_service
- **utils**: app.models, app.models, app.models, app.models
- **sync_tasks**: app.tasks, app.services.auto_sync_service, app.realtime, app.services.scheduled_sync_service, app.services.auto_sync_service, app.services.scheduled_sync_service, app.realtime, app.realtime
- **daily_report**: app.tasks, app.models, app.utils.email_sender, app.ai
- **synchronization**: app.models, app.services.curriculum_bridge_service, app.services.auto_sync_service, app.services.sync_service, app.models, app.models, app.models, app.models, app.models
- **dashboard**: app.models, app.utils.model_helpers, app.models
- **student_evaluation**: app.models, app.ai, app.ai.helpers, app.models
- **class_management**: app.models, app.utils.model_helpers
- **curriculum_management**: app.models, app.ai, app.services.curriculum_bridge_service
- **approval_workflow**: app.models, app.services.unit_completion_service
- **progress_manager**: app.core.base_service, app.models, app.core.data_access, app.core.data_access, app.core.data_access, app.core.data_access
- **data_collector**: app.models
- **persistence_service**: app.models
- **goals_todos**: app.models, app.utils.model_helpers
- **activities**: app.models
- **surveys**: app.models


## 🗃️ Database Models

### ReviewSet
- Table: `review_sets`
- Fields: 20
- Relationships: 0

### ReviewSetItem
- Table: `review_set_items`
- Fields: 17
- Relationships: 0

### CurriculumUnit
- Table: `curriculum_units`
- Fields: 26
- Relationships: 0

### UnitItemMapping
- Table: `unit_item_mappings`
- Fields: 10
- Relationships: 0

### StudentUnitSelection
- Table: `student_unit_selections`
- Fields: 27
- Relationships: 0

### ClassLearningSettings
- Table: `class_learning_settings`
- Fields: 20
- Relationships: 0

### LearningPath
- Table: `learning_paths`
- Fields: 13
- Relationships: 0

### EmailLog
- Table: `email_logs`
- Fields: 24
- Relationships: 0

### AIRecommendation
- Table: `ai_recommendations`
- Fields: 19
- Relationships: 0

### SpeechTranscription
- Table: `speech_transcriptions`
- Fields: 17
- Relationships: 0

### Subject
- Table: `subjects`
- Fields: 13
- Relationships: 0

