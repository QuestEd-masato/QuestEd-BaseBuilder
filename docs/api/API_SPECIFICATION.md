# QuestEd API Specification

*📅 Last Updated: 2025-07-21 | Status: Consolidated Production Reference*

This document provides comprehensive API specification combining REST API endpoints, authentication, and integration guidelines for the QuestEd educational platform.

---

## 🎯 API Overview

### Base Configuration
- **Base URL**: `/api/`
- **Authentication**: JWT token-based
- **Rate Limiting**: Flask-Limiter protection
- **Response Format**: Standardized JSON with consistent error handling
- **CORS**: Configured for cross-origin requests
- **Version**: v1.0 (Production Stable)

### Response Standards
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful",
  "errors": null,
  "timestamp": "2025-07-21T10:30:00Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "data": null,
  "message": "Validation error",
  "errors": {
    "field_name": ["Error description"]
  },
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-07-21T10:30:00Z"
}
```

---

## 🔐 Authentication Endpoints

### POST /api/login
User authentication with JWT token generation

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "jwt_token_string",
    "user": {
      "id": 123,
      "username": "user123",
      "role": "student",
      "school_id": 1,
      "full_name": "Test User"
    },
    "expires_at": "2025-07-22T10:30:00Z"
  }
}
```

### POST /api/logout
User logout and token invalidation

**Headers:** `{"Authorization": "Bearer jwt_token"}`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### GET /api/user/profile
Get current user profile information

**Headers:** `{"Authorization": "Bearer jwt_token"}`

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "username": "user123",
      "full_name": "Test User",
      "email": "user@example.com",
      "role": "student",
      "school_id": 1,
      "email_confirmed": true,
      "is_approved": true
    }
  }
}
```

### POST /api/auth/refresh-token
Refresh JWT token before expiration

**Headers:** `{"Authorization": "Bearer jwt_token"}`

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "new_jwt_token_string",
    "expires_at": "2025-07-22T10:30:00Z"
  }
}
```

---

## 📚 Curriculum & Learning Endpoints

### GET /api/units
List available curriculum units

**Query Parameters:**
- `school_id`: integer (optional, filtered by user's school)
- `subject_id`: integer (optional)
- `difficulty_level`: 1-5 (optional)
- `page`: integer (default: 1)
- `limit`: integer (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "units": [
      {
        "id": 1,
        "title": "Introduction to Science",
        "difficulty_level": 2,
        "estimated_minutes": 45,
        "subject_id": 1,
        "school_id": 1,
        "description": "Basic scientific concepts",
        "learning_objectives": ["Understand scientific method", "Basic experiments"]
      }
    ],
    "pagination": {
      "total": 50,
      "page": 1,
      "limit": 20,
      "pages": 3
    }
  }
}
```

### POST /api/units/select
Student unit selection for learning

**Request:**
```json
{
  "unit_id": 1,
  "class_id": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "selection": {
      "id": 123,
      "student_id": 45,
      "unit_id": 1,
      "class_id": 5,
      "status": "not_started",
      "selected_at": "2025-07-21T10:30:00Z",
      "estimated_completion": "2025-07-21T11:15:00Z"
    }
  }
}
```

### GET /api/progress
Student learning progress tracking

**Query Parameters:**
- `student_id`: integer (required for teachers/admins)
- `unit_id`: integer (optional)
- `class_id`: integer (optional)
- `timeframe`: 'week'|'month'|'semester' (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "progress": {
      "total_units": 10,
      "completed_units": 3,
      "in_progress_units": 2,
      "completion_rate": 30.0,
      "study_time_minutes": 180,
      "average_score": 85.2,
      "last_activity": "2025-07-21T09:15:00Z"
    },
    "unit_progress": [
      {
        "unit_id": 1,
        "status": "completed",
        "score": 92,
        "time_spent": 45,
        "completed_at": "2025-07-20T14:30:00Z"
      }
    ]
  }
}
```

### GET /api/proficiency
Proficiency level tracking by category

**Query Parameters:**
- `student_id`: integer (optional for teachers/admins)
- `category_id`: integer (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "proficiencies": [
      {
        "category_id": 1,
        "category_name": "Mathematics",
        "level": 3,
        "progress_percentage": 75.0,
        "last_updated": "2025-07-21T14:20:00Z",
        "recommended_actions": ["Practice multiplication tables", "Review fractions"]
      }
    ]
  }
}
```

### POST /api/units/complete
Mark unit as completed with submission

**Request:**
```json
{
  "unit_id": 1,
  "class_id": 5,
  "completion_data": {
    "answers": {...},
    "time_spent": 45,
    "difficulty_rating": 3
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "completion": {
      "unit_id": 1,
      "status": "pending_approval",
      "score": 88,
      "submitted_at": "2025-07-21T10:30:00Z"
    },
    "recommendations": [
      {
        "type": "next_unit",
        "unit_id": 2,
        "reason": "Natural progression"
      }
    ]
  }
}
```

---

## 🤖 AI Integration Endpoints

### POST /api/chat
AI-powered chat interface

**Request:**
```json
{
  "message": "Explain photosynthesis",
  "subject_id": 1,
  "class_id": 5,
  "context": "curriculum_discussion",
  "conversation_id": "conv_123" // optional for continuing conversation
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "response": "Photosynthesis is the process by which plants convert sunlight into energy...",
    "ai_model": "gpt-4",
    "conversation_id": "conv_123",
    "timestamp": "2025-07-21T10:30:00Z",
    "suggested_followups": [
      "What are the products of photosynthesis?",
      "How does chlorophyll work in this process?"
    ]
  }
}
```

### GET /api/recommendations
AI-generated learning recommendations

**Query Parameters:**
- `student_id`: integer
- `recommendation_type`: 'weakness_improvement'|'next_learning'|'review_topics'
- `limit`: integer (default: 5)

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "type": "weakness_improvement",
        "content": "Focus on multiplication tables",
        "confidence_score": 0.85,
        "recommended_units": [1, 3, 5],
        "estimated_time": 30,
        "priority": "high"
      },
      {
        "type": "review_topics",
        "content": "Review fraction concepts from last month",
        "confidence_score": 0.72,
        "recommended_units": [7],
        "estimated_time": 20,
        "priority": "medium"
      }
    ]
  }
}
```

### POST /api/ai/generate-content
Generate educational content using AI

**Request:**
```json
{
  "content_type": "theme"|"question"|"explanation",
  "subject_id": 1,
  "difficulty_level": 2,
  "topic": "Basic algebra",
  "parameters": {
    "target_audience": "middle_school",
    "learning_style": "visual"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "generated_content": {
      "title": "Understanding Variables in Algebra",
      "content": "Variables are like mystery boxes...",
      "type": "explanation",
      "estimated_reading_time": 5
    },
    "metadata": {
      "ai_model": "gpt-4",
      "generation_time": 2.3,
      "quality_score": 0.91
    }
  }
}
```

---

## 📊 Analytics & Ranking Endpoints

### GET /api/rankings
Performance ranking system

**Query Parameters:**
- `ranking_type`: 'total_points'|'weekly_points'|'accuracy_rate'|'study_time'
- `scope`: 'school'|'class'
- `scope_id`: integer
- `limit`: integer (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "rankings": [
      {
        "rank_position": 1,
        "student_id": 45,
        "student_name": "Test Student",
        "score": 950,
        "change_from_last_week": "+2",
        "detailed_stats": {
          "total_points": 950,
          "accuracy_rate": 92.4,
          "study_time_hours": 15.5,
          "units_completed": 8
        }
      }
    ],
    "total_participants": 25,
    "user_rank": 5,
    "ranking_updated_at": "2025-07-21T08:00:00Z"
  }
}
```

### GET /api/analytics
Learning analytics dashboard

**Query Parameters:**
- `timeframe`: 'week'|'month'|'semester'
- `class_id`: integer (optional)
- `student_id`: integer (optional for individual analytics)

**Response:**
```json
{
  "success": true,
  "data": {
    "analytics": {
      "total_activities": 150,
      "average_score": 85.2,
      "completion_rate": 78.5,
      "improvement_trend": "+5.2%",
      "engagement_metrics": {
        "daily_active_users": 35,
        "session_duration_avg": 25.5,
        "peak_activity_hours": ["10:00", "14:00", "19:00"]
      },
      "subject_performance": [
        {
          "subject_id": 1,
          "subject_name": "Mathematics",
          "average_score": 88.1,
          "completion_rate": 82.0
        }
      ]
    }
  }
}
```

### POST /api/data-integrity/verify
Data integrity verification service

**Request:**
```json
{
  "verification_type": "unit_mappings"|"user_enrollments"|"progress_records",
  "fix_inconsistencies": false,
  "scope": {
    "school_id": 1,
    "class_id": 5
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "verification_results": {
      "total_checked": 500,
      "inconsistencies_found": 3,
      "fixed_automatically": 0,
      "manual_review_required": 3,
      "issues": [
        {
          "type": "orphaned_selection",
          "description": "Student unit selection without valid unit",
          "affected_records": 1,
          "severity": "medium"
        }
      ]
    }
  }
}
```

---

## 🎯 BaseBuilder API Endpoints

### GET /api/basebuilder/categories
Problem categories management

**Query Parameters:**
- `subject_id`: integer (optional)
- `include_stats`: boolean (default: false)

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": 1,
        "name": "Mathematics",
        "description": "Basic math problems",
        "subject_id": 1,
        "problem_count": 150,
        "text_count": 25,
        "difficulty_range": [1, 5],
        "created_at": "2025-06-01T10:00:00Z"
      }
    ]
  }
}
```

### GET /api/basebuilder/problems
Problem management and retrieval

**Query Parameters:**
- `category_id`: integer (optional)
- `difficulty`: 1-5 (optional)
- `subject_id`: integer (optional)
- `random`: boolean (default: false)
- `limit`: integer (default: 10)

**Response:**
```json
{
  "success": true,
  "data": {
    "problems": [
      {
        "id": 1,
        "title": "Basic Addition",
        "question": "What is 2 + 2?",
        "answer_type": "multiple_choice",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4",
        "difficulty": 1,
        "category_id": 1,
        "explanation": "When you add 2 and 2, you get 4.",
        "estimated_time": 1
      }
    ]
  }
}
```

### POST /api/basebuilder/session/start
Learning session initiation

**Request:**
```json
{
  "category_id": 1,
  "difficulty_level": 2,
  "problem_count": 10,
  "session_type": "practice"|"test"|"review"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session": {
      "session_id": "session_123",
      "problems": [...], // Array of problem objects
      "estimated_duration": 15,
      "session_type": "practice",
      "start_time": "2025-07-21T10:30:00Z"
    }
  }
}
```

### POST /api/basebuilder/session/complete
Complete learning session with answers

**Request:**
```json
{
  "session_id": "session_123",
  "answers": [
    {
      "problem_id": 1,
      "answer": "4",
      "time_spent": 30
    }
  ],
  "completion_status": "completed"|"partial"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": {
      "session_id": "session_123",
      "total_problems": 10,
      "correct_answers": 8,
      "accuracy_rate": 80.0,
      "total_time": 12.5,
      "score": 800,
      "proficiency_changes": [
        {
          "category_id": 1,
          "old_level": 2,
          "new_level": 3
        }
      ]
    },
    "next_recommendations": [
      {
        "category_id": 2,
        "reason": "Ready for next level"
      }
    ]
  }
}
```

---

## 🔧 API Security & Performance

### Authentication Security
- **JWT Token Expiration**: 24 hours (configurable)
- **Token Refresh**: Automatic refresh before expiration
- **Role-based Access**: Endpoint access by user role
- **School Isolation**: Data filtered by user's school
- **Rate Limiting**: Configurable per endpoint

### Rate Limiting Configuration
```python
# Default rate limits
@limiter.limit("100 per hour")     # General API access
@limiter.limit("10 per minute")    # Authentication endpoints
@limiter.limit("50 per minute")    # Data retrieval
@limiter.limit("5 per minute")     # File upload operations
@limiter.limit("20 per minute")    # AI chat endpoints
```

### Input Validation
- Required field validation
- Data type validation
- Range validation (difficulty: 1-5)
- SQL injection prevention
- XSS protection on all inputs
- File upload security (16MB max)

### Response Time Targets
- **Authentication**: <1 second
- **Data Retrieval**: <2 seconds
- **Complex Analytics**: <5 seconds
- **AI Generation**: <10 seconds
- **File Upload**: <10 seconds (16MB max)

---

## 🔄 API Versioning & Compatibility

### Current Version: v1.0
- **Base Path**: `/api/`
- **Stability**: Production stable
- **Backward Compatibility**: Maintained for existing clients
- **Support Timeline**: Minimum 12 months

### Future Versioning Strategy
- **v2 Planning**: Microservices migration preparation
- **Breaking Changes**: Will be introduced with clear migration path
- **Deprecation Policy**: 6-month notice for endpoint deprecation
- **Migration Support**: Detailed migration guides and tools

---

## 📝 Development Guidelines

### Adding New Endpoints
1. **Blueprint Organization**: Add to appropriate Blueprint
2. **Authentication**: Apply `@login_required` decorator
3. **Authorization**: Use `@require_roles()` for role-specific access
4. **Validation**: Implement comprehensive input validation
5. **Error Handling**: Use standardized error response format
6. **Rate Limiting**: Apply appropriate rate limiting
7. **Documentation**: Update API specification
8. **Testing**: Write comprehensive API tests

### Testing API Endpoints
```bash
# Manual testing with curl
curl -X GET "http://localhost:5000/api/units" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json"

# Automated testing (recommended)
pytest tests/api/test_endpoints.py -v
```

### Error Handling Best Practices
- Use appropriate HTTP status codes
- Provide clear error messages
- Include validation details for input errors
- Log errors for debugging (without sensitive data)
- Implement graceful degradation

---

## 📚 Lesson System Routes

### Teacher Lesson Management Routes

#### GET /lesson-system/teacher/lesson-management
Main lesson management interface for teachers
- **Access**: Teacher role required
- **Description**: Display all lessons with filtering options

#### GET /lesson-system/teacher/analytics
Lesson analytics dashboard
- **Access**: Teacher role required
- **Description**: View lesson statistics and student progress

#### GET /lesson-system/teacher/curriculum/{curriculum_id}/lessons
View lessons for specific curriculum
- **Access**: Teacher role required
- **Parameters**: curriculum_id (integer)

### Student Lesson Routes

#### GET /lesson-system/curriculum/{curriculum_id}/lessons
View curriculum lessons as student
- **Access**: Student role required
- **Parameters**: curriculum_id (integer)

#### GET /lesson-system/lesson/{lesson_id}
View lesson details
- **Access**: Student role required
- **Parameters**: lesson_id (integer)

### Common URL Mistakes
⚠️ **Important**: The following URLs are **incorrect** and will return 404:
- ❌ `/lesson-system/teacher/lessons` → ✅ Use `/lesson-system/teacher/lesson-management`
- ❌ `/lesson-system/teacher/create-lesson` → ✅ Use POST to `/lesson-system/lesson/create`

---

**🔌 This consolidated API specification provides comprehensive endpoint documentation for QuestEd. Update this document when API changes occur.**