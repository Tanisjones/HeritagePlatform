"""
Translation configuration for education app models.
Registers fields for multilingual support (Spanish, English, Quechua).
"""

from modeltranslation.translator import translator, TranslationOptions
from .models import (
    LOMGeneral, LOMEducational, LOMClassification,
    EducationalResource, ResourceType, ResourceCategory
)


class LOMGeneralTranslationOptions(TranslationOptions):
    """Translation options for LOMGeneral model."""
    fields = ('title', 'description', 'keywords', 'coverage')


class LOMEducationalTranslationOptions(TranslationOptions):
    """Translation options for LOMEducational model."""
    fields = ('description',)


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


# Register models for translation
translator.register(LOMGeneral, LOMGeneralTranslationOptions)
translator.register(LOMEducational, LOMEducationalTranslationOptions)
translator.register(LOMClassification, LOMClassificationTranslationOptions)
translator.register(ResourceType, ResourceTypeTranslationOptions)
translator.register(ResourceCategory, ResourceCategoryTranslationOptions)
translator.register(EducationalResource, EducationalResourceTranslationOptions)
