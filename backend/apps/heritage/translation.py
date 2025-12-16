"""
Translation configuration for heritage app models.
Registers fields for multilingual support (Spanish, English, Quechua).
"""

from modeltranslation.translator import translator, TranslationOptions
from .models import (
    HeritageCategory, HeritageType, Parish, HeritageItem, Annotation
)


class HeritageCategoryTranslationOptions(TranslationOptions):
    """Translation options for HeritageCategory model."""
    fields = ('name', 'description')


class HeritageTypeTranslationOptions(TranslationOptions):
    """Translation options for HeritageType model."""
    fields = ('name', 'description')


class ParishTranslationOptions(TranslationOptions):
    """Translation options for Parish model."""
    fields = ('name',)


class HeritageItemTranslationOptions(TranslationOptions):
    """Translation options for HeritageItem model."""
    fields = ('title', 'description', 'address')


class AnnotationTranslationOptions(TranslationOptions):
    """Translation options for Annotation model."""
    fields = ('content',)


# Register models for translation
translator.register(HeritageCategory, HeritageCategoryTranslationOptions)
translator.register(HeritageType, HeritageTypeTranslationOptions)
translator.register(Parish, ParishTranslationOptions)
translator.register(HeritageItem, HeritageItemTranslationOptions)
translator.register(Annotation, AnnotationTranslationOptions)
