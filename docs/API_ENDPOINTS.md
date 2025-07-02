# QuestEd API Endpoints Reference

*📅 Last Updated: 2025-07-02 | Status: Production Stable*

This document provides comprehensive API endpoint documentation, including recent fixes and endpoint modifications.

---

## 🎯 API Overview

### Base Configuration
- **Base URL**: `/api/`
- **Authentication**: JWT token-based
- **Rate Limiting**: Flask-Limiter protection
- **Response Format**: Standardized JSON with consistent error handling
- **CORS**: Configured for cross-origin requests

### Response Standards
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful",
  "errors": null,
  "timestamp": "2025-07-02T10:30:00Z"
}
```

---

## 🔐 Authentication Endpoints

### POST /api/login
User authentication with JWT token generation
```json
Request:
{
  "username": "string",
  "password": "string"
}

Response:
{
  "success": true,
  "data": {
    "token": "jwt_token_string",
    "user": {
      "id": 123,
      "username": "user123",
      "role": "student",
      "school_id": 1
    }
  }
}
```

### POST /api/logout
User logout and token invalidation
```json
Headers: {"Authorization": "Bearer jwt_token"}
Response: {"success": true, "message": "Logged out successfully"}
```

### GET /api/user/profile
Get current user profile information
```json
Headers: {"Authorization": "Bearer jwt_token"}
Response:
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "username": "user123",
      "full_name": "Test User",
      "email": "user@example.com",
      "role": "student",
      "school_id": 1
    }
  }
}
```

---

## 📚 Curriculum & Learning Endpoints

### GET /api/units
List available curriculum units
```json
Query Parameters:
- school_id: integer (optional, filtered by user's school)
- subject_id: integer (optional)
- difficulty_level: 1-5 (optional)

Response:
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
        "school_id": 1
      }
    ]
  }
}
```

### POST /api/units/select
Student unit selection (CRITICAL FIX APPLIED 2025-06-25)
```json
Request:
{
  "unit_id": 1,
  "class_id": 5
}

Response:
{
  "success": true,
  "data": {
    "selection": {
      "id": 123,
      "student_id": 45,
      "unit_id": 1,
      "class_id": 5,
      "status": "not_started",
      "selected_at": "2025-07-02T10:30:00Z"
    }
  }
}
```

**🔧 Fix Applied (2025-06-25)**: Removed duplicate endpoint definition that was causing "undefined" errors

### GET /api/progress
Student learning progress tracking
```json
Query Parameters:
- student_id: integer (required for teachers/admins)
- unit_id: integer (optional)
- class_id: integer (optional)

Response:
{
  "success": true,
  "data": {
    "progress": {
      "total_units": 10,
      "completed_units": 3,
      "in_progress_units": 2,
      "completion_rate": 30.0,
      "study_time_minutes": 180
    }
  }
}
```

### GET /api/proficiency
Proficiency level tracking
```json
Response:
{
  "success": true,
  "data": {
    "proficiencies": [
      {
        "category_id": 1,
        "category_name": "Mathematics",
        "level": 3,
        "last_updated": "2025-07-01T14:20:00Z"
      }
    ]
  }
}
```

---

## 🤖 AI Integration Endpoints

### POST /api/chat
AI-powered chat interface
```json
Request:
{
  "message": "Explain photosynthesis",
  "subject_id": 1,
  "class_id": 5,
  "context": "curriculum_discussion"
}

Response:
{
  "success": true,
  "data": {
    "response": "Photosynthesis is the process...",
    "ai_model": "gpt-4",
    "timestamp": "2025-07-02T10:30:00Z"
  }
}
```

### GET /api/recommendations
AI-generated learning recommendations
```json
Query Parameters:
- student_id: integer
- recommendation_type: string

Response:
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "type": "weakness_improvement",
        "content": "Focus on multiplication tables",
        "confidence_score": 0.85,
        "recommended_units": [1, 3, 5]
      }
    ]
  }
}
```

---

## 📊 Analytics & Ranking Endpoints

### GET /api/rankings
Performance ranking system
```json
Query Parameters:
- ranking_type: 'total_points'|'weekly_points'|'accuracy_rate'|'study_time'
- scope: 'school'|'class'
- scope_id: integer

Response:
{
  "success": true,
  "data": {
    "rankings": [
      {
        "rank_position": 1,
        "student_id": 45,
        "student_name": "Test Student",
        "score": 950,
        "detailed_stats": {
          "total_points": 950,
          "accuracy_rate": 92.4,
          "study_time_hours": 15.5
        }
      }
    ],
    "total_participants": 25
  }
}
```

### GET /api/analytics
Learning analytics dashboard
```json
Query Parameters:
- timeframe: 'week'|'month'|'semester'
- class_id: integer (optional)

Response:
{
  "success": true,
  "data": {
    "analytics": {
      "total_activities": 150,
      "average_score": 85.2,
      "completion_rate": 78.5,
      "engagement_metrics": {
        "daily_active_users": 35,
        "session_duration_avg": 25.5
      }
    }
  }
}
```

### POST /api/data-integrity/verify
Data integrity verification service (Added Phase 3)
```json
Request:
{
  "verification_type": "unit_mappings",
  "fix_inconsistencies": false
}

Response:
{
  "success": true,
  "data": {
    "verification_results": {
      "total_checked": 500,
      "inconsistencies_found": 3,
      "fixed_automatically": 0,
      "manual_review_required": 3
    }
  }
}
```

---

## 🎯 BaseBuilder API Endpoints

### GET /api/basebuilder/categories
Problem categories management
```json
Response:
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": 1,
        "name": "Mathematics",
        "description": "Basic math problems",
        "problem_count": 150,
        "text_count": 25
      }
    ]
  }
}
```

### GET /api/basebuilder/problems
Problem management and retrieval
```json
Query Parameters:
- category_id: integer (optional)
- difficulty: 1-5 (optional)
- subject_id: integer (optional)

Response:
{
  "success": true,
  "data": {
    "problems": [
      {
        "id": 1,
        "title": "Basic Addition",
        "question": "What is 2 + 2?",
        "answer_type": "multiple_choice",
        "difficulty": 1,
        "category_id": 1
      }
    ]
  }
}
```

### POST /api/basebuilder/session/start
Learning session initiation
```json
Request:
{
  "category_id": 1,
  "difficulty_level": 2,
  "problem_count": 10
}

Response:
{
  "success": true,
  "data": {
    "session": {
      "session_id": "session_123",
      "problems": [...],
      "estimated_duration": 15
    }
  }
}
```

---

## 🔧 Critical Endpoint Fixes (2025-06-25 to 2025-07-02)

### API Endpoint Duplication Fix (2025-06-25)
**Problem**: Duplicate `/api/units/select` endpoint causing "undefined" responses
**Solution**: Removed duplicate definition, consolidated to single implementation
**Impact**: Resolved student unit selection errors

### Blueprint Endpoint Updates (2025-06-30)
**Problem**: 199+ template references to incorrect Blueprint endpoints
**Solution**: Systematic update across 59 template files
**Examples**:
```
teacher.dashboard → teacher_dashboard.dashboard
student.activities → student_activities.activities
basebuilder_module.problems → problems.problems
```

### Template Variable Fixes (2025-06-30)
**Problem**: Missing template variables causing API response errors
**Solution**: Added all required variables with appropriate defaults
**Impact**: Eliminated UndefinedError exceptions

### Model Field Consistency (2025-06-30)
**Problem**: Inconsistent field naming in API responses
**Solution**: Standardized on `updated_at` pattern throughout
**Impact**: Consistent API response structure

---

## 📈 API Performance Metrics

### Response Time Targets
- **Authentication**: <1 second
- **Data Retrieval**: <2 seconds  
- **Complex Analytics**: <5 seconds
- **File Upload**: <10 seconds (16MB max)

### Rate Limiting Configuration
```python
# Default rate limits
@limiter.limit("100 per hour")     # General API access
@limiter.limit("10 per minute")    # Authentication endpoints
@limiter.limit("50 per minute")    # Data retrieval
@limiter.limit("5 per minute")     # File upload operations
```

### Error Rate Monitoring
- **Target Error Rate**: <0.1%
- **Current Status**: Minimal errors (major issues resolved)
- **Monitoring**: Real-time error tracking and alerting

---

## 🛡️ API Security

### Authentication Security
- **JWT Token Expiration**: 24 hours (configurable)
- **Token Refresh**: Automatic refresh before expiration
- **Role-based Access**: Endpoint access by user role
- **School Isolation**: Data filtered by user's school

### Input Validation
```python
# Request validation patterns
- Required field validation
- Data type validation  
- Range validation (difficulty: 1-5)
- SQL injection prevention
- XSS protection on all inputs
```

### Error Handling
```json
# Standardized error response
{
  "success": false,
  "data": null,
  "message": "Validation error",
  "errors": {
    "field_name": ["Error description"]
  },
  "error_code": "VALIDATION_ERROR"
}
```

---

## 🔄 API Versioning Strategy

### Current Version: v1
- **Base Path**: `/api/`
- **Stability**: Production stable
- **Backward Compatibility**: Maintained for existing clients

### Future Versioning
- **v2 Planning**: Microservices migration preparation
- **Breaking Changes**: Will be introduced with clear migration path
- **Deprecation**: 6-month notice for endpoint deprecation

---

## 📝 Development Guidelines

### Adding New Endpoints
1. **Blueprint Organization**: Add to appropriate Blueprint
2. **Authentication**: Apply `@login_required` decorator
3. **Authorization**: Use `@require_roles()` for role-specific access
4. **Validation**: Implement comprehensive input validation
5. **Error Handling**: Use standardized error response format
6. **Documentation**: Update this document with new endpoints

### Testing API Endpoints
```bash
# Manual testing with curl
curl -X GET "http://localhost:5000/api/units" \
  -H "Authorization: Bearer your_jwt_token"

# Automated testing (recommended)
pytest tests/api/test_endpoints.py
```

### Rate Limiting Considerations
- **User Experience**: Balance security with usability
- **Peak Load**: Consider school hours usage patterns
- **Error Messages**: Clear rate limit exceeded messages
- **Monitoring**: Track rate limit hits for optimization

---

**🔌 This API reference provides comprehensive endpoint documentation for QuestEd. Update this document when API changes occur.**