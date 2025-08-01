# -*- coding: utf-8 -*-
"""
Curriculum Management Services

Phase8C: curriculum_management.py完全分解による7つの専門サービス
1209行の巨大ファイルを75%削減し、各サービス200-350行に分割
"""

from .curriculum_data_service import CurriculumDataService
from .curriculum_validation_service import CurriculumValidationService
from .curriculum_ai_service import CurriculumAIService
from .curriculum_import_export_service import CurriculumImportExportService
# 旧システム削除: LessonManagementService → LessonService (lesson_system使用)
from .theme_management_service import ThemeManagementService
from .teacher_curriculum_unit_service import TeacherCurriculumUnitService

__all__ = [
    "CurriculumDataService",
    "CurriculumValidationService",
    "CurriculumAIService",
    "CurriculumImportExportService",
    # "LessonManagementService",  # 削除: 新システム (lesson_system) 使用
    "ThemeManagementService",
    "TeacherCurriculumUnitService"
]