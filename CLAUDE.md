# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuestEd is a Flask-based educational platform with multi-role support (admin, teacher, student), featuring school management, AI-powered curriculum generation, and student tracking capabilities.

## Development Commands

### Running the Application
```bash
# Development mode
python app.py

# Using Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run

# Production with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Database Management
```bash
# Initialize migrations
flask db init

# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migrations
flask db downgrade
```

### Environment Setup
Create a `.env` file with:
- `SECRET_KEY` - Flask secret key
- `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` - MySQL database credentials
- `OPENAI_API_KEY` - OpenAI API key for AI features
- `FLASK_ENV` - development/production
- `FLASK_DEBUG` - true/false

## Architecture Overview

### Application Structure (Refactored to Blueprints)
- **run.py** - Main entry point for running the application
- **app/** - Main application package with Blueprint structure
  - **__init__.py** - Application factory and initialization
  - **models/** - All database models (User, Class, School, etc.)
  - **auth/** - Authentication routes (login, register, password reset)
  - **admin/** - Admin functionality (user/school management)
  - **teacher/** - Teacher features (class management, evaluations)
  - **student/** - Student features (activities, surveys, themes)
  - **ai/** - AI integration (OpenAI API functions)
  - **api/** - REST API endpoints
- **config.py** - Configuration classes for different environments
- **extensions.py** - Shared Flask extension instances (db, migrate, login_manager, admin, csrf)

### Legacy Structure
- **app_old.py** - Original monolithic application (4831 lines) - kept for reference
- **app_factory.py** - Original application factory pattern

### Additional Modules
- **core/** - Academic, enrollment, and school management blueprints
- **basebuilder/** - Learning management system with problems, texts, and proficiency tracking
- **templates/** - Jinja2 templates organized by feature area
- **static/** - CSS, JavaScript, and uploaded files

### Database Models

#### User System
- `User` - Multi-role users (admin, teacher, student) with email verification
- `School` - School entities with unique codes
- `SchoolYear` - Academic year tracking
- `ClassGroup` - Classes within school years
- `StudentEnrollment` - Student-class relationships

#### Educational Content
- `Class` - Teacher-owned classes
- `MainTheme` - Class-level themes
- `InquiryTheme` - Student personal themes
- `Curriculum` - Class curriculums with JSON data
- `Milestone` - Class milestones for student submissions

#### Student Data
- `InterestSurvey` - Student interests (JSON)
- `PersonalitySurvey` - Student personality data (JSON)
- `ActivityLog` - Student activities with optional images
- `Todo` - Student task management
- `Goal` - Student goals with progress tracking
- `StudentEvaluation` - Teacher evaluations

#### BaseBuilder Module
- `ProblemCategory` - Problem categorization
- `BasicKnowledgeItem` - Individual problems
- `TextSet` - Text collections for reading comprehension
- `LearningPath` - Structured learning sequences
- `ProficiencyRecord` - Student mastery tracking

### Key Features

#### Authentication & Authorization
- Email verification required for new users
- Teacher approval for student accounts
- Role-based access control (admin, teacher, student)
- Password reset via email tokens
- JWT token-based API authentication
- Session management with security headers

#### AI Integration
- OpenAI GPT-4 for curriculum generation
- AI-powered theme suggestions
- Student evaluation assistance
- Chat interface for educational support
- Personalized learning recommendations
- Automated weakness analysis and review generation

#### Data Import/Export
- CSV import for users and students
- Curriculum import/export
- Activity log export to PDF
- Evaluation export to CSV

#### Security Enhancements (New)
- Comprehensive input validation and sanitization
- XSS and SQL injection protection
- Rate limiting for API endpoints
- Secure error handling with detailed logging
- Database query auditing and monitoring
- Encrypted storage for sensitive data
- CORS configuration for secure API access

### Common Patterns

#### Route Protection
```python
@login_required  # Requires authentication
if current_user.role != 'teacher':  # Role checking
    flash('この機能は教師のみ利用可能です。')
    return redirect(url_for('index'))
```

#### Database Operations
```python
# Always use try-except for database operations
try:
    db.session.add(new_object)
    db.session.commit()
    flash('Success message')
except Exception as e:
    db.session.rollback()
    flash(f'Error: {str(e)}')
```

#### File Uploads
- Images stored in `static/uploads/`
- Filename sanitization with timestamps
- Allowed extensions: jpg, jpeg, png, gif
- Max file size: 16MB

#### Security Utilities (New)
```python
# Input validation and sanitization
from app.utils.input_validator import InputValidator
validated_data = InputValidator.validate_and_sanitize(form_data, validation_rules)

# Secure error handling
from app.utils.error_handler import ErrorHandler
response_data, status_code = ErrorHandler.handle_exception(error)

# Database security
from app.utils.database_security import SecureQueryBuilder
query, params = SecureQueryBuilder.build_safe_select('users', ['id', 'username'], {'role': 'student'})

# API security decorators
from app.utils.api_security import APISecurityDecorator

@APISecurityDecorator.require_api_auth(['teacher', 'admin'])
@APISecurityDecorator.rate_limit(limit=100, window=3600)
@APISecurityDecorator.log_api_access()
def secure_api_endpoint():
    return jsonify({'data': 'secure response'})
```

### Testing
Currently no automated tests. To add tests:
1. Create `tests/` directory
2. Use pytest with Flask test client
3. Test database operations with test database from `TestingConfig`

### Important Notes
- Japanese UI - All user-facing text is in Japanese
- MySQL/PyMySQL for database (not SQLite)
- Flask-Admin for administrative interface
- CSRF protection enabled globally
- All datetime stored in UTC

## Database Structure (Detailed Report 2025-06-24)

### Database Overview
- **MySQL Version**: 8.0.40
- **Character Set**: utf8mb4_unicode_ci
- **Total Tables**: 59 (including 2 views)
- **Database Size**: 3.39 MB
- **Active Students**: 46 users (40 students, 5 teachers, 1 admin)

### Critical Field Name Consistency
⚠️ **IMPORTANT**: Ensure field naming consistency across the application:

#### ✅ Standardized Fields (Fixed)
- **Difficulty**: Use `difficulty_level` everywhere (NOT `difficulty`)
- **Timestamps**: Use `timestamp` for ActivityLog, `created_at` for others
- **User References**: Context-dependent (`student_id` vs `user_id`)

#### 🔧 Fixed Issues
- `static/js/learning_portal.js`: Updated `unit.difficulty` → `unit.difficulty_level`
- `app/api/__init__.py`: Consistent use of `difficulty_level` field
- `app/services/ranking_service.py`: Fixed tuple access patterns

### Core Table Structure

#### Users & Authentication (46 total users)
```sql
users:
- id (PK), username (UNIQUE), full_name, email (UNIQUE)  
- role ('admin'|'teacher'|'student'), school_id (FK)
- email_confirmed, is_approved, is_active
- password, reset_token, token_created_at
```

#### Educational Content
```sql
curriculums: (6 active)
- id (PK), class_id (FK), teacher_id (FK), subject_id (FK)
- title, description, content (JSON), format
- is_converted_to_units (BOOLEAN) -- NEW: Bridge feature
- units_conversion_date, curriculum_data (TEXT) -- NEW
- created_by (FK) -- NEW: Bridge relationship

curriculum_units: (8 active) 
- id (PK), title, description, unit_code (UNIQUE)
- difficulty_level (1-3), estimated_minutes, order_index
- school_id (FK), created_by (FK), subject_id (FK)
- legacy_curriculum_id (FK) -- NEW: Bridge to original curriculum
- is_active, tags (JSON), learning_objectives
```

#### Bridge System Tables (NEW)
```sql
auto_sync_settings: (0 records)
- id (PK), curriculum_id (FK UNIQUE)
- auto_sync_enabled, sync_on_curriculum_update, sync_on_item_change
- conflict_resolution_strategy, sync_delay_minutes, batch_sync_window
- last_sync_at, created_at, updated_at

sync_logs: (0 records)
- id (PK), curriculum_id (FK), trigger_type, status
- message (TEXT), details (JSON), created_at
```

#### Learning Records
```sql
answer_records: (3,456 records, 92.4% accuracy)
- id (PK), student_id (FK), problem_id (FK)
- is_correct, response_time, created_at

student_unit_selections: (546 records)
- id (PK), student_id (FK), unit_id (FK), class_id (FK)
- status ('not_started'|'in_progress'|'completed')
- study_time_minutes, completion_rate, selected_at
```

### Data Distribution & Usage

#### Subject Distribution
- **English**: 475 problems (97.3%) - Most active
- **Integrated Studies**: 13 problems (2.7%)
- **Science**: 3 curriculum units  
- **Other subjects**: Minimal content

#### School Distribution  
- **KGUJHS**: 38 users, 3 classes (Primary school)
- **Test01**: 4 users, 5 classes (Development)
- **TEST**: 3 users, 0 classes (Testing)

#### Learning Activity
- **Total Attempts**: 3,793 across 21 active students
- **Problem Coverage**: 200 unique problems used
- **Average Accuracy**: 92.4% (very high performance)
- **Top Performer**: 山口　琉叶 (1,565 correct / 1,710 attempts)

### Bridge System Implementation Status

#### ✅ Completed Features
1. **Phase 1**: Basic curriculum-to-unit conversion
2. **Phase 2**: Integrated management dashboard  
3. **Phase 3**: Automatic synchronization system

#### Database Schema Changes
```sql
-- Bridge-related fields added to existing tables
ALTER TABLE curriculums ADD COLUMN is_converted_to_units BOOLEAN DEFAULT FALSE;
ALTER TABLE curriculum_units ADD COLUMN legacy_curriculum_id INT;

-- New tables for auto-sync functionality  
CREATE TABLE auto_sync_settings (...);
CREATE TABLE sync_logs (...);
```

### Performance & Indexing

#### Key Indexes
- `users`: email (UNIQUE), username (UNIQUE), class_id
- `curriculum_units`: unit_code (UNIQUE), is_active, school_id, created_by
- `answer_records`: student_id, problem_id (high query volume)
- `curriculums`: is_converted_to_units (NEW - for bridge queries)

#### Query Patterns
- **High Volume**: answer_records (3,456 rows), basic_knowledge_items (488 rows)
- **Bridge Queries**: curriculum ↔ curriculum_units relationships
- **Real-time**: student_unit_selections for learning portal

### Foreign Key Relationships

#### Bridge System Relationships
```
curriculums ←→ curriculum_units (via legacy_curriculum_id)
curriculums → auto_sync_settings (1:1)
curriculums → sync_logs (1:many)
```

#### Core Educational Flow
```
schools → classes → curriculums → curriculum_units
       → users → student_unit_selections → learning_records
```

### Database Maintenance Commands

#### Investigation Commands
```bash
# Generate comprehensive DB report
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" < generate_db_report.sql

# Check field consistency
grep -rn "difficulty[^_]" app/ --include="*.py" | grep -v "difficulty_level"

# Monitor error logs
sudo journalctl -u quested -f | grep -E "(ERROR|WARNING)"

# Verify bridge system tables
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT COUNT(*) as curriculum_count, 
       SUM(is_converted_to_units) as converted_count 
FROM curriculums;"
```

#### Performance Monitoring
```bash
# Check slow queries
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SHOW VARIABLES LIKE 'slow_query_log%';
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;"

# Monitor connection usage
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Connections';"
```

### Troubleshooting Common Issues

#### Field Name Mismatches
1. ✅ **Fixed**: `difficulty` → `difficulty_level` in JavaScript
2. ✅ **Fixed**: Ranking service tuple access patterns
3. ⚠️ **Monitor**: New bridge features for consistency

#### Bridge System Health Check
```bash
# Verify bridge functionality
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT c.id, c.title, c.is_converted_to_units,
       COUNT(cu.id) as unit_count
FROM curriculums c
LEFT JOIN curriculum_units cu ON c.id = cu.legacy_curriculum_id
GROUP BY c.id;"
```

#### Missing Column Errors
If "Unknown column" errors occur:
1. Check if migrations need to run: `flask db upgrade`
2. Verify column exists: `SHOW COLUMNS FROM table_name`
3. Restart application server: `sudo systemctl restart quested`

### Data Integrity Checks

#### Orphaned Records Detection
```bash
# Find curriculum units without parent curriculum
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT cu.* FROM curriculum_units cu 
LEFT JOIN curriculums c ON cu.legacy_curriculum_id = c.id 
WHERE cu.legacy_curriculum_id IS NOT NULL AND c.id IS NULL;"

# Find broken user references
source .env && mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT 'student_unit_selections' as table_name, COUNT(*) as broken_refs
FROM student_unit_selections sus
LEFT JOIN users u ON sus.student_id = u.id
WHERE u.id IS NULL;"
```