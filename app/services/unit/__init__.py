# -*- coding: utf-8 -*-
"""
Unit Management Services

Phase8A: unit_management.py完全分解による8つの専門サービス
1766行の神ファイルを80%削減し、各サービス200-300行に分割
"""

from .unit_data_service import UnitDataService
from .student_progress_service import StudentProgressService
from .completion_workflow_service import CompletionWorkflowService
from .unit_mapping_service import UnitMappingService
from .teacher_statistics_service import TeacherStatisticsService
from .access_control_service import AccessControlService
from .curriculum_integration_service import CurriculumIntegrationService
from .unit_orchestration_service import UnitOrchestrationService

__all__ = [
    "UnitDataService",
    "StudentProgressService", 
    "CompletionWorkflowService",
    "UnitMappingService",
    "TeacherStatisticsService",
    "AccessControlService",
    "CurriculumIntegrationService",
    "UnitOrchestrationService"
]