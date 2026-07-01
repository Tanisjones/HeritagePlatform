"""
Translation configuration for routes app models.
Registers user-facing text fields for multilingual support (Spanish default,
English). Run ``makemigrations routes`` + ``migrate`` + ``sync_translation_fields``
after changing this file.
"""

from modeltranslation.translator import translator, TranslationOptions
from .models import HeritageRoute, RouteStop


class HeritageRouteTranslationOptions(TranslationOptions):
    """Translation options for HeritageRoute model."""
    fields = ('title', 'description', 'theme', 'accessibility_notes', 'cost_notes')


class RouteStopTranslationOptions(TranslationOptions):
    """Translation options for RouteStop model."""
    fields = ('arrival_instructions',)


translator.register(HeritageRoute, HeritageRouteTranslationOptions)
translator.register(RouteStop, RouteStopTranslationOptions)
