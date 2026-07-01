"""
Translation configuration for education app models.
Registers fields for multilingual support (Spanish, English, Quechua).
"""

from modeltranslation.translator import translator, TranslationOptions
from .models import (
    LOMGeneral, LOMEducational, LOMClassification,
    EducationalResource, ResourceType, ResourceCategory,
    AssessmentQuestion, LessonPlan, LessonActivity
)


class LOMGeneralTranslationOptions(TranslationOptions):
    """Translation options for LOMGeneral model."""
    fields = ('title', 'description', 'keywords', 'coverage')


class LOMEducationalTranslationOptions(TranslationOptions):
    """Translation options for LOMEducational model."""
    fields = ('description', 'prerequisites', 'competencies', 'suggested_activities')


class LOMClassificationTranslationOptions(TranslationOptions):
    """Translation options for LOMClassification model."""
    fields = ('description', 'keywords')


class ResourceTypeTranslationOptions(TranslationOptions):
    """Translation options for ResourceType model."""
    fields = ('name',)


class ResourceCategoryTranslationOptions(TranslationOptions):
    """Translation options for ResourceCategory model."""
    fields = ('name',)


class EducationalResourceTranslationOptions(TranslationOptions):
    """Translation options for EducationalResource model."""
    fields = ('title', 'description', 'content')


class AssessmentQuestionTranslationOptions(TranslationOptions):
    """Translation options for AssessmentQuestion model."""
    fields = ('prompt', 'feedback')


class LessonPlanTranslationOptions(TranslationOptions):
    """Translation options for LessonPlan model."""
    fields = ('title', 'summary', 'curriculum_alignment')


class LessonActivityTranslationOptions(TranslationOptions):
    """Translation options for LessonActivity model."""
    fields = ('title', 'instructions', 'materials')


# Register models for translation
translator.register(LOMGeneral, LOMGeneralTranslationOptions)
translator.register(LOMEducational, LOMEducationalTranslationOptions)
translator.register(LOMClassification, LOMClassificationTranslationOptions)
translator.register(ResourceType, ResourceTypeTranslationOptions)
translator.register(ResourceCategory, ResourceCategoryTranslationOptions)
translator.register(EducationalResource, EducationalResourceTranslationOptions)
translator.register(AssessmentQuestion, AssessmentQuestionTranslationOptions)
translator.register(LessonPlan, LessonPlanTranslationOptions)
translator.register(LessonActivity, LessonActivityTranslationOptions)
