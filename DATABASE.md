# QuestEd Database Reference

*📅 Last Updated: 2025-07-02 | Authority: Single Source of Truth*

This document provides comprehensive database schema, models, and relationship information for the QuestEd educational platform.

---

## 🎯 Database Overview

### Production Configuration
- **MySQL Version**: 8.0.40
- **Character Set**: utf8mb4_unicode_ci
- **Total Tables**: 55 confirmed tables
- **Database Size**: 3.39 MB (production)
- **Active Users**: 46 total (40 students, 5 teachers, 1 admin)

### Connection Information
```bash
# Local MySQL Connection
mysql -u QuestEd -p'QuestEd-03012025MySQL' -h localhost -P 3306 quested
```

⚠️ **WARNING**: Do not modify the local database casually. Always backup before structural changes.

---

## 📊 Current Data Volume

### User Distribution
- **Students**: 40 active users
- **Teachers**: 5 active users  
- **Administrators**: 1 active user

### Learning Activity Metrics
- **Answer Records**: 3,811 total (92.4% accuracy rate)
- **Unit Selections**: 546 active student selections
- **Word Proficiency**: 642 tracking records
- **Active Curricula**: 6 legacy curricula
- **Modern Units**: 8 curriculum units

---

## 🗄️ Database Schema Reference

### Core User System (6 tables)

#### users
Primary user table with multi-role support
```sql
users:
- id (PK), username (UNIQUE), full_name, email (UNIQUE)
- role ('admin'|'teacher'|'student'), school_id (FK)
- class_id (FK) -- Direct class assignment for students
- is_active, email_confirmed, is_approved
- email_token, token_created_at
- reset_token, reset_token_created_at
- created_at, updated_at
```

#### schools
School management hierarchy
```sql
schools:
- id (PK), name, code (UNIQUE), address, contact_email
- created_at

school_years:
- id (PK), school_id (FK), year, is_current
- start_date, end_date

class_groups:
- id (PK), school_year_id (FK), teacher_id (FK)
- name, description, grade, created_at

student_enrollments:
- id (PK), student_id (FK), class_group_id (FK), school_year_id (FK)
- student_number, enrolled_at, is_active
- UNIQUE(student_id, class_group_id, school_year_id)
```

#### subjects
Subject management with AI integration
```sql
subjects:
- id (PK), name, code (UNIQUE)
- ai_system_prompt, learning_objectives, assessment_criteria
- grade_level, is_active, created_at, updated_at
```

### Educational Structure (8 tables)

#### classes
Class management
```sql
classes:
- id (PK), teacher_id (FK), school_id (FK), subject_id (FK)
- name, description, schedule, location, created_at

class_enrollments:
- id (PK), class_id (FK), student_id (FK)
- enrolled_at, is_active
- UNIQUE(class_id, student_id)
```

#### curriculums (Legacy System)
```sql
curriculums:
- id (PK), class_id (FK), teacher_id (FK), subject_id (FK)
- title, description, content (JSON), format
- is_converted_to_units, units_conversion_date
- created_by (FK), created_at, updated_at
```

#### curriculum_units (Modern System)
```sql
curriculum_units:
- id (PK), subject_id (FK), unit_code (UNIQUE), title, description
- difficulty_level (1-5), estimated_minutes, prerequisites (JSON)
- learning_objectives, tags (JSON), order_index
- is_active, school_id (FK), created_by (FK)
- legacy_curriculum_id (FK), created_at, updated_at

unit_item_mappings:
- id (PK), unit_id (FK), item_id (FK)
- weight, order_index, is_required, created_at
- UNIQUE(unit_id, item_id)

student_unit_selections:
- id (PK), student_id (FK), unit_id (FK), class_id (FK)
- status ('not_started'|'in_progress'|'completed'|'paused')
- progress_percentage, total_items, completed_items, correct_items
- started_at, completed_at, last_activity_at, study_time_minutes
- approval_status ('none'|'pending'|'approved'|'rejected')
- completion_request_date, teacher_comments, approved_by (FK)
- created_at, updated_at

class_learning_settings:
- id (PK), class_id (FK) UNIQUE
- allow_free_progress, require_unit_order, max_concurrent_units
- min_completion_rate, allow_unit_skip, show_difficulty_level
- require_teacher_approval, auto_approve_threshold
- created_by (FK), created_at, updated_at
```

### BaseBuilder Module (13 tables)

#### Problem Management
```sql
problem_categories:
- id (PK), name, description, parent_id (FK to self)
- school_id (FK), subject_id (FK)
- created_at, created_by (FK)

basic_knowledge_items:
- id (PK), category_id (FK), title, question, answer_type
- correct_answer, choices (JSON), explanation
- difficulty (1-5) -- CRITICAL: "difficulty" not "difficulty_level"
- subject_id (FK), text_set_id (FK), order_in_text, school_id (FK)
- created_at, created_by (FK), is_active
```

#### Text Management
```sql
text_sets:
- id (PK), title, description, category_id (FK)
- school_id (FK), created_at, created_by (FK)

text_deliveries:
- id (PK), text_set_id (FK), class_id (FK), delivered_by (FK)
- delivered_at, due_date

text_proficiency_records:
- id (PK), student_id (FK), text_set_id (FK)
- level (0-100%), updated_at
- UNIQUE(student_id, text_set_id)
```

#### Learning Progress Tracking
```sql
answer_records:
- id (PK), student_id (FK), problem_id (FK)
- student_answer, is_correct, answer_time, created_at

proficiency_records:
- id (PK), student_id (FK), category_id (FK)
- level (0-5), updated_at, review_date, last_reviewed
- UNIQUE(student_id, category_id)

word_proficiency_records:
- id (PK), student_id (FK), problem_id (FK)
- level (0-5), updated_at, review_date
- UNIQUE(student_id, problem_id)
```

#### Learning Paths
```sql
basebuilder_learning_paths:
- id (PK), title, description, steps (JSON)
- created_at, created_by (FK), is_active, school_id (FK)

path_assignments:
- id (PK), path_id (FK), student_id (FK), assigned_by (FK)
- assigned_at, due_date, completed, progress
- UNIQUE(path_id, student_id)

knowledge_theme_relations:
- id (PK), problem_id (FK), theme_id (FK)
- relevance (1-5), created_at, created_by (FK)
```

### Student Activity System (8 tables)

#### Surveys and Themes
```sql
interest_surveys:
- id (PK), student_id (FK), responses (JSON), submitted_at

personality_surveys:
- id (PK), student_id (FK), responses (JSON), submitted_at

main_themes:
- id (PK), teacher_id (FK), class_id (FK)
- title, description, created_at, updated_at

inquiry_themes:
- id (PK), student_id (FK), class_id (FK), main_theme_id (FK)
- title, question, description, rationale, approach, potential
- is_ai_generated, is_selected, created_at
```

#### Activity Management
```sql
activity_logs:
- id (PK), student_id (FK), class_id (FK)
- title, date, content, reflection, image_url
- activity, tags, created_at

todos:
- id (PK), student_id (FK), title, description
- due_date, priority, is_completed, created_at, updated_at

goals:
- id (PK), student_id (FK), title, description
- goal_type, due_date, progress (0-100), is_completed
- created_at, updated_at

student_evaluations:
- id (PK), student_id (FK), class_id (FK)
- evaluation_text, created_at, updated_at
```

### AI and Communication (8 tables)

#### Chat System
```sql
chat_history:
- id (PK), user_id (FK), class_id (FK), subject_id (FK)
- message, is_user, created_at
```

#### Speech and AI Features
```sql
speech_transcriptions:
- id (PK), student_id (FK), session_id
- original_audio_text, cleaned_text, confidence_score
- language_code, audio_duration, input_context
- context_id, is_processed, error_message
- created_at, updated_at

ai_recommendations:
- id (PK), student_id (FK), recommendation_type
- context_data (JSON), ai_model, prompt_template
- ai_response, recommended_items (JSON), confidence_score
- reasoning, is_accepted, is_effective, feedback_text
- session_id, created_at, updated_at
```

#### Review System
```sql
review_sets:
- id (PK), student_id (FK), title, description
- generation_type, target_weakness_areas (JSON)
- difficulty_level, total_problems, estimated_time_minutes
- review_type, status, expires_at, generated_by_ai
- ai_generation_params (JSON), created_at, updated_at

review_set_items:
- id (PK), review_set_id (FK), problem_id (FK)
- order_index, weight, expected_difficulty
- weakness_category, selection_reason, is_completed
- student_answer, is_correct, time_spent_seconds
- attempts_count, completed_at

email_logs:
- id (PK), recipient_email, subject, body
- status, sent_at, error_message, created_at
```

### Administrative System (12 tables)

#### Group Management
```sql
groups:
- id (PK), name, description, class_id (FK)
- created_by (FK), created_at

group_memberships:
- id (PK), group_id (FK), student_id (FK), joined_at
- UNIQUE(group_id, student_id)

milestones:
- id (PK), class_id (FK), title, description
- due_date, created_at

rubric_templates:
- id (PK), class_id (FK), teacher_id (FK)
- title, description, content (JSON)
- created_at, updated_at
```

#### Ranking System
```sql
rankings:
- id (PK), student_id (FK), school_id (FK), class_id (FK)
- ranking_type ('total_points'|'weekly_points'|'monthly_points'|'accuracy_rate'|'study_time'|'consistency')
- period_start, period_end, rank_position, score
- total_participants, detailed_stats (JSON)
- calculated_at, is_current

ranking_cache:
- id (PK), cache_key (UNIQUE), ranking_type
- scope ('school'|'class'), scope_id
- ranking_data (JSON), participant_count
- created_at, expires_at, updated_at
```

---

## 🔗 Critical Relationship Patterns

### Multi-Role User System
```
User (role: admin/teacher/student)
├── school_id → School
├── class_id → Class (direct assignment for students)
├── Student relationships:
│   ├── StudentEnrollment → ClassGroup → SchoolYear
│   ├── ClassEnrollment → Class (many-to-many)
│   ├── StudentUnitSelection → CurriculumUnit
│   └── AnswerRecord → BasicKnowledgeItem
├── Teacher relationships:
│   ├── classes_teaching → Class
│   ├── ClassGroup.teacher_id
│   └── curriculum_units.created_by
└── Admin: Full access across all entities
```

### Educational Content Hierarchy
```
Subject
├── Classes → Teacher → Students
├── CurriculumUnit → UnitItemMapping → BasicKnowledgeItem
├── ChatHistory (subject-specific conversations)
└── ProblemCategory → BasicKnowledgeItem
```

### Learning Progress Flow
```
Student → StudentUnitSelection → CurriculumUnit
       └→ UnitItemMapping → BasicKnowledgeItem → AnswerRecord
                         └→ WordProficiency (individual tracking)
                         └→ ProficiencyRecord (category tracking)
```

### School-Based Data Isolation
```
School
├── Users (teachers, students)
├── SchoolYear → ClassGroup → StudentEnrollment
├── CurriculumUnit (school_id for custom units)
├── TextSet (school_id for school-specific texts)
└── BaseBuilderLearningPath (school_id for custom paths)
```

---

## 📏 Field Naming Standards

### ✅ Confirmed Standards

#### Primary Keys and Foreign Keys
```sql
id (PK)                           -- Primary key
{table_name}_id (FK)              -- Foreign key reference
student_id (FK to users.id)       -- ✅ Student-specific references
user_id (FK to users.id)          -- ✅ General user references
teacher_id (FK to users.id)       -- ✅ Teacher-specific references
school_id (FK to schools.id)      -- ✅ School references
class_id (FK to classes.id)       -- ✅ Class references
```

#### Critical Field Distinctions
```sql
-- BaseBuilder module
difficulty (INTEGER 1-5)          -- ✅ basic_knowledge_items.difficulty

-- Curriculum module  
difficulty_level (INTEGER 1-3)    -- ✅ curriculum_units.difficulty_level
```

#### Timestamp Fields
```sql
created_at (DATETIME)             -- ✅ All tables
updated_at (DATETIME)             -- ✅ Tables with modification tracking
last_updated (DATETIME)           -- ✅ Legacy naming in proficiency_records
submitted_at (DATETIME)           -- ✅ Survey-specific timestamps
```

#### Status and State Fields
```sql
is_active (BOOLEAN)               -- ✅ Entity activation state
is_completed (BOOLEAN)            -- ✅ Task completion state
is_current (BOOLEAN)              -- ✅ Current period/selection
status (ENUM)                     -- ✅ Workflow states with defined values
```

---

## 🔧 Database Integrity

### Critical Foreign Key Relationships
```sql
-- User system integrity
users.school_id → schools.id (ON DELETE SET NULL)
users.class_id → classes.id (ON DELETE SET NULL)

-- Educational hierarchy integrity  
classes.teacher_id → users.id (ON DELETE CASCADE)
classes.subject_id → subjects.id (ON DELETE SET NULL)
curriculum_units.subject_id → subjects.id (ON DELETE SET NULL)

-- Learning tracking integrity
student_unit_selections.student_id → users.id (ON DELETE CASCADE)
student_unit_selections.unit_id → curriculum_units.id (ON DELETE CASCADE)
answer_records.student_id → users.id (ON DELETE CASCADE)
answer_records.problem_id → basic_knowledge_items.id (ON DELETE CASCADE)
```

### Data Consistency Rules
```sql
-- Unique constraints preventing data duplication
UNIQUE(student_id, unit_id, class_id)     -- student_unit_selections
UNIQUE(student_id, category_id)           -- proficiency_records  
UNIQUE(student_id, problem_id)            -- word_proficiency_records
UNIQUE(unit_id, item_id)                  -- unit_item_mappings
UNIQUE(class_id)                          -- class_learning_settings

-- Business logic constraints
curriculum_units.difficulty_level (1-5)
basic_knowledge_items.difficulty (1-5)  
student_unit_selections.progress_percentage (0.00-100.00)
proficiency_records.level (0-5)
```

---

## 📈 Performance Considerations

### Critical Indexes
```sql
-- User queries
users: username, email (unique constraints)
-- Learning progress queries
student_unit_selections: student_id, unit_id, class_id (composite)
answer_records: student_id, problem_id (query optimization)
-- Content queries
basic_knowledge_items: category_id, difficulty, subject_id
curriculum_units: subject_id, difficulty_level, school_id
```

### Query Optimization Patterns
- Use `joinedload` for eager loading relationships
- Composite indexes for multi-column filtering
- Proper pagination for large datasets
- Caching for frequently accessed reference data

---

## ⚠️ Development Guidelines

### Safe Operations
- ✅ SELECT queries for data exploration
- ✅ INSERT operations for new records
- ✅ UPDATE operations with proper WHERE clauses
- ✅ Database backups before any structural changes

### Prohibited Operations
- ❌ DROP TABLE without explicit approval
- ❌ ALTER TABLE without migration scripts
- ❌ DELETE operations without backup
- ❌ Direct manipulation of foreign key relationships

### Migration Best Practices
1. Always create migration scripts for schema changes
2. Test migrations on development database first
3. Backup production data before applying migrations
4. Verify data integrity after migration completion

---

**📚 This database reference serves as the authoritative source for all schema information. Update this document when database changes occur.**