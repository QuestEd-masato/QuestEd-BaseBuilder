# QuestEd Architecture Reference

*📅 Last Updated: 2025-07-02 | Status: Blueprint Architecture Confirmed*

This document provides comprehensive architecture, Blueprint structure, and technical specifications for the QuestEd educational platform.

---

## 🏗️ System Architecture Overview

### Technology Stack
- **Backend**: Python 3.8+, Flask 2.x
- **Database**: MySQL 8.0.40 with SQLAlchemy ORM
- **Frontend**: Jinja2 templates, Bootstrap 5, jQuery
- **API**: RESTful JSON with standardized error handling
- **AI Integration**: OpenAI GPT-4, GPT-3.5-turbo
- **Deployment**: Docker, Gunicorn, Nginx

### Architecture Pattern
**Modular Blueprint Architecture** - Transitioned from monolithic (4,831-line app.py) to organized modular structure with clear separation of concerns.

---

## 📂 Blueprint Structure

### Application Layout
```
app/
├── __init__.py              # Application factory and initialization
├── models/                  # Database models (SQLAlchemy)
├── auth/                    # Authentication Blueprint
├── admin/                   # Administrative Blueprint
├── teacher/                 # Teacher functionality Blueprint
├── student/                 # Student functionality Blueprint
├── ai/                      # AI integration Blueprint
├── api/                     # REST API Blueprint
├── core/                    # Academic management Blueprints
├── basebuilder/             # Learning management Blueprint
├── services/                # Business logic layer
├── utils/                   # Utility functions
└── tasks/                   # Background tasks
```

### Blueprint Registration Flow
```python
# Application initialization sequence
app/__init__.py
├── create_app() factory function
├── Flask extensions initialization
├── Blueprint registration:
│   ├── auth_bp (Authentication)
│   ├── admin_bp (Administration) 
│   ├── teacher_bp (Teacher features)
│   ├── student_bp (Student features)
│   ├── ai_bp (AI integration)
│   ├── api_bp (REST API)
│   └── basebuilder modules (Learning management)
└── Error handlers and context processors
```

---

## 🔐 Authentication Blueprint

### Structure
```
app/auth/
├── __init__.py              # Blueprint definition
├── secure_auth.py           # Main authentication routes
└── password_validator.py    # Password validation utilities
```

### Key Endpoints
```python
# Authentication routes
/login                       # User login
/logout                      # User logout  
/register                    # New user registration
/verify_email/<token>        # Email verification
/forgot_password            # Password reset request
/reset_password/<token>     # Password reset confirmation
/change_password            # Password change for authenticated users
```

### Security Features
- Email verification required for new accounts
- Teacher approval required for student accounts
- Password strength validation (12+ characters)
- Time-limited reset tokens
- CSRF protection on all forms
- Session management with secure cookies

---

## 👨‍💼 Admin Blueprint

### Structure
```
app/admin/
├── __init__.py              # Blueprint definition
├── user_management.py       # User administration
├── school_management.py     # School administration
└── analytics.py            # Administrative analytics
```

### Key Endpoints
```python
# User management
/admin/users                 # User listing and management
/admin/pending_users         # Pending approval queue
/admin/schools              # School management
/admin/analytics            # System analytics dashboard

# School management  
/admin/school_years         # Academic year management
/admin/class_groups         # Class group administration
/admin/student_enrollment   # Student enrollment management
```

### Administrative Features
- Multi-role user management (admin/teacher/student)
- School hierarchy management
- Real-time analytics dashboard
- Bulk user operations (CSV import/export)
- System monitoring and health checks

---

## 👨‍🏫 Teacher Blueprint

### Modular Structure
```
app/teacher/
├── __init__.py              # Blueprint definition and registration
├── common.py               # Shared teacher utilities
├── pdf_generator.py        # PDF export functionality
└── modules/                # Modular teacher features
    ├── dashboard.py        # Teacher dashboard
    ├── class_management.py # Class and student management  
    ├── curriculum_management.py # Curriculum creation/editing
    ├── student_evaluation.py # Student assessment
    ├── approval_workflow.py # Student submission approvals
    ├── synchronization.py  # Data synchronization
    └── analytics.py        # Teacher analytics
```

### Key Endpoints
```python
# Dashboard and overview
/teacher/dashboard          # Main teacher dashboard
/teacher/classes           # Class listing and management

# Class management
/teacher/create_class      # New class creation
/teacher/class/<id>        # Individual class management
/teacher/students/<class_id> # Student management for class

# Curriculum and content
/teacher/curriculums       # Curriculum management
/teacher/create_curriculum # New curriculum creation
/teacher/themes            # Theme management
/teacher/milestones        # Milestone management

# Student interaction
/teacher/evaluations       # Student evaluations
/teacher/pending_approvals # Unit completion approvals
/teacher/chat              # AI-powered chat interface

# Analytics and reporting
/teacher/analytics         # Class performance analytics
/teacher/ranking_analysis  # Student ranking analysis
/teacher/export_activities # Activity export to PDF
```

### Teacher Features
- Class creation and management
- Curriculum development with AI assistance
- Student progress monitoring
- Approval workflow for student submissions
- Performance analytics and reporting
- AI-powered educational content generation

---

## 👨‍🎓 Student Blueprint

### Modular Structure
```
app/student/
├── __init__.py              # Blueprint definition and registration
├── utils.py                # Student utility functions
└── modules/                # Modular student features
    ├── dashboard.py        # Student dashboard
    ├── activities.py       # Activity management
    ├── goals_todos.py      # Goals and todo management
    ├── surveys.py          # Interest and personality surveys
    └── themes.py           # Theme exploration
```

### Key Endpoints
```python
# Dashboard and overview
/student/dashboard          # Main student dashboard
/student/classes           # Enrolled classes view

# Learning activities
/student/activities        # Activity management
/student/create_activity   # New activity creation
/student/learning_portal   # Learning unit selection

# Personal development
/student/goals             # Goal setting and tracking
/student/todos             # Task management
/student/themes            # Personal theme exploration

# Surveys and assessment
/student/interest_survey   # Interest assessment
/student/personality_survey # Personality assessment

# Progress and performance
/student/ranking           # Performance rankings
/student/milestones        # Milestone tracking
```

### Student Features
- Personalized learning dashboard
- Activity logging with reflection
- Goal setting and progress tracking
- Interest and personality surveys
- Theme-based inquiry learning
- Progress visualization and rankings

---

## 🤖 AI Blueprint

### Structure
```
app/ai/
├── __init__.py              # Blueprint definition
├── helpers.py              # Core AI integration functions
└── curriculum_helpers.py   # Curriculum-specific AI functions
```

### AI Integration Features
- **OpenAI GPT-4**: Advanced curriculum generation
- **GPT-3.5-turbo**: Chat interactions and content suggestions
- **Subject-specific prompts**: Tailored AI responses by subject
- **Context-aware recommendations**: Based on student progress
- **Automated content generation**: Themes, questions, explanations

### Key Functions
```python
# AI-powered content generation
generate_curriculum()       # Curriculum creation assistance
generate_themes()          # Theme suggestions
generate_evaluation()      # Student evaluation assistance
chat_with_ai()            # Interactive AI chat
analyze_student_weakness() # Learning gap analysis
```

---

## 🔌 API Blueprint

### Structure
```
app/api/
├── __init__.py              # Blueprint definition and base configurations
├── base.py                 # Base API classes and utilities
├── admin_teacher.py        # Admin and teacher API endpoints
├── chat_ai.py             # AI chat API
├── data_integrity.py      # Data integrity services
├── rankings.py            # Ranking system API
├── review_system.py       # Review and assessment API
├── student_tools.py       # Student-specific API tools
└── unit_management.py     # Curriculum unit management API
```

### API Endpoints
```python
# Authentication and user management
/api/login                  # API authentication
/api/user/profile          # User profile management

# Curriculum and learning
/api/units                 # Curriculum unit operations
/api/units/select          # Unit selection for students
/api/progress              # Learning progress tracking
/api/proficiency           # Proficiency assessments

# AI and chat
/api/chat                  # AI chat interface
/api/recommendations       # AI-generated recommendations

# Analytics and reporting
/api/rankings              # Performance rankings
/api/analytics             # Learning analytics
/api/data-integrity        # Data consistency verification
```

### API Standards
- **Response Format**: Standardized JSON with consistent error handling
- **Authentication**: JWT token-based authentication
- **Rate Limiting**: Flask-Limiter protection
- **Error Handling**: Comprehensive exception management
- **Documentation**: OpenAPI/Swagger specifications

---

## 🎯 BaseBuilder Blueprint

### Comprehensive Structure
```
basebuilder/
├── __init__.py              # Module initialization with init_app()
├── routes.py               # Central Blueprint registration hub
├── models.py               # BaseBuilder-specific models
├── utils.py                # Common utilities and decorators
├── services.py             # Business logic services
├── exporters.py            # Data export functionality
├── importers.py            # Data import functionality
└── routes/                 # Individual route modules
    ├── __init__.py         # Empty (prevents circular imports)
    ├── categories.py       # Problem category management
    ├── problems.py         # Problem management
    ├── sessions.py         # Learning session management
    ├── progress.py         # Progress tracking and analytics
    ├── analytics.py        # Advanced analytics and reporting
    └── admin.py            # Administrative functions
```

### BaseBuilder Endpoints (17 confirmed)
```python
# Main dashboard
/basebuilder/               # Role-based dashboard redirect

# Category management
/basebuilder/categories     # Category listing and management
/basebuilder/create_category # Category creation

# Problem management
/basebuilder/problems       # Problem listing and management
/basebuilder/create_problem # Problem creation
/basebuilder/solve_problem  # Problem solving interface

# Learning sessions
/basebuilder/start_session  # Session initiation
/basebuilder/session_summary # Session completion summary

# Progress tracking
/basebuilder/proficiency    # Proficiency level tracking
/basebuilder/history        # Learning history view

# Text management
/basebuilder/text_sets      # Text collection management
/basebuilder/deliver_text   # Text delivery to classes

# Analytics
/basebuilder/analysis       # Performance analysis
/basebuilder/student_analysis # Individual student analysis

# Administration
/basebuilder/learning_paths # Learning path management
/basebuilder/import_problems # Problem import functionality
/basebuilder/import_text    # Text import functionality
```

### BaseBuilder Technical Specifications
- **Blueprint Unification**: All modules use `/basebuilder/` prefix
- **Template Structure**: 30 HTML templates covering all functionality
- **Service Layer**: Modular business logic in `services.py`
- **Utility Functions**: Common operations in `utils.py`
- **Quality Rating**: ⭐⭐⭐⭐ (Very Good - Structure Confirmed)

---

## 🔧 Core Services Layer

### Service Architecture
```
app/services/
├── __init__.py              # Service layer initialization
├── base_service.py         # Base service class
├── curriculum_service.py   # Curriculum management
├── ai_recommendation_service.py # AI recommendations
├── ranking_service.py      # Performance rankings
├── speech_service.py       # Speech-to-text integration
├── auto_sync_service.py    # Automated synchronization
├── weakness/               # Weakness analysis services
│   ├── pattern_analyzer.py # Learning pattern analysis
│   ├── recommendation_generator.py # Weakness-based recommendations
│   └── statistics_calculator.py # Statistical analysis
└── progress/               # Progress tracking services
    └── unified_progress_service.py # Unified progress management
```

### Service Patterns
- **Base Service Class**: Common functionality inheritance
- **Dependency Injection**: Service composition and testing
- **Error Handling**: Standardized exception management
- **Logging**: Comprehensive operation logging
- **Caching**: Performance optimization strategies

---

## 🛡️ Security Architecture

### Authentication & Authorization
```python
# Multi-role authentication system
User roles: ['admin', 'teacher', 'student']

# Role-based access control
@login_required                    # Authentication required
@require_roles('teacher', 'admin') # Role-specific access
@school_access_required           # School-based data isolation
```

### Security Layers
1. **Input Validation**: Comprehensive form and API input validation
2. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
3. **XSS Protection**: Template escaping and content sanitization
4. **CSRF Protection**: Global CSRF token validation
5. **Session Security**: Secure cookie configuration
6. **File Upload Security**: Type validation and secure storage
7. **Rate Limiting**: API request throttling

### Data Privacy
- **School-based Isolation**: Users can only access their school's data
- **Role-based Filtering**: Data access based on user role
- **Audit Logging**: Comprehensive activity tracking
- **Data Encryption**: Sensitive data encryption at rest

---

## 📊 Performance Architecture

### Database Optimization
```sql
-- Critical performance indexes
users: username, email (unique)
student_unit_selections: student_id, unit_id, class_id (composite)
answer_records: student_id, problem_id (query optimization)
basic_knowledge_items: category_id, difficulty, subject_id
curriculum_units: subject_id, difficulty_level, school_id
```

### Caching Strategy
- **Application Cache**: Flask-Caching for view functions
- **Database Cache**: Query result caching for reference data
- **Session Cache**: Redis for session storage (configurable)
- **Static Asset Cache**: CDN and browser caching

### Performance Targets
- **Response Time**: <3 seconds average (achieved)
- **Concurrent Users**: 100+ simultaneous users
- **Database Queries**: Optimized with eager loading
- **File Uploads**: 16MB maximum with progress tracking

---

## 🔄 Data Flow Architecture

### Request Processing Flow
```
User Request → Authentication → Authorization → Blueprint Router
     ↓
Route Handler → Service Layer → Model Layer → Database
     ↓
Response → Template Rendering → HTML/JSON Response
```

### Learning Progress Flow
```
Student Activity → Answer Records → Proficiency Calculation
     ↓
Weakness Analysis → AI Recommendations → Review Set Generation
     ↓
Targeted Practice → Progress Update → Performance Analytics
```

### Content Creation Flow
```
Teacher Input → AI Enhancement → Content Validation
     ↓
Database Storage → Student Access → Progress Tracking
     ↓
Analytics Collection → Performance Reports → Improvement Recommendations
```

---

## 🚀 Deployment Architecture

### Container Structure
```
docker-compose.yml
├── quested-app (Flask application)
├── mysql (Database service)
├── redis (Caching service - optional)
└── nginx (Reverse proxy - production)
```

### Environment Configurations
- **Development**: Flask dev server with debug mode
- **Staging**: Gunicorn with limited resources
- **Production**: Gunicorn + Nginx with full optimization

### Scalability Considerations
- **Horizontal Scaling**: Multi-instance deployment ready
- **Database Scaling**: Master-slave replication capability
- **Static Assets**: CDN integration prepared
- **Load Balancing**: Nginx configuration included

---

## 📈 Monitoring & Observability

### Application Monitoring
```python
# Health check endpoints
/health                     # Basic application health
/health/database           # Database connectivity
/health/dependencies       # External service status

# Metrics collection
- Response time tracking
- Error rate monitoring  
- User activity analytics
- Performance bottleneck identification
```

### Logging Strategy
- **Application Logs**: Structured logging with Python logging
- **Access Logs**: Nginx access and error logs
- **Database Logs**: MySQL slow query and error logs
- **Security Logs**: Authentication and authorization events

---

## 🔮 Future Architecture Evolution

### Microservices Migration Plan
```
Current Monolithic Architecture → Target Microservices Architecture

Planned Services (8 total):
├── User Management Service (Authentication, RBAC)
├── Academic Management Service (Schools, classes, enrollment)
├── Content Management Service (Curriculum, themes, media)
├── Learning Analytics Service (Progress tracking, performance)
├── Assessment Service (Surveys, evaluations, grading)
├── AI Services (OpenAI integration, recommendations)
├── Notification Service (Email, alerts, communications)
└── BaseBuilder Service (LMS functionality)
```

### Migration Strategy
- **Phase-by-phase extraction**: Gradual service separation
- **API-first approach**: RESTful service interfaces
- **Event-driven communication**: Asynchronous message passing
- **Database-per-service**: Data ownership and isolation
- **16-week implementation timeline**: Structured migration plan

---

**🏗️ This architecture reference provides comprehensive technical specifications for QuestEd. Update this document when architectural changes occur.**