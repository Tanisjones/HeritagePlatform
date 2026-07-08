"""
Translation configuration for cities app models.
"""

from modeltranslation.translator import translator, TranslationOptions
from .models import City


class CityTranslationOptions(TranslationOptions):
    """Translation options for City model."""
    fields = ('name', 'description', 'country_name')


translator.register(City, CityTranslationOptions)
