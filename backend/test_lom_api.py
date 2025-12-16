#!/usr/bin/env python
"""
Script to test LOM metadata API endpoints.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.heritage.models import HeritageItem
from apps.education.models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights, LOMClassification, LOMContributor
)

def test_lom_creation():
    """Test creating LOM metadata for a heritage item."""

    # Get the first heritage item
    heritage_item = HeritageItem.objects.first()
    if not heritage_item:
        print("❌ No heritage items found. Create one first.")
        return False

    print(f"✓ Found heritage item: {heritage_item.title}")

    # Check if LOM metadata already exists
    if hasattr(heritage_item, 'lom_general'):
        print(f"✓ LOM metadata already exists for this item")
        lom = heritage_item.lom_general
    else:
        # Create LOM General metadata
        lom = LOMGeneral.objects.create(
            heritage_item=heritage_item,
            title=heritage_item.title,
            language='es',
            description=f"Recurso educativo sobre {heritage_item.title}",
            keywords="patrimonio, cultura, educación, Ecuador, Riobamba",
            coverage="Riobamba, Chimborazo, Ecuador - Siglo XX",
            structure='atomic',
            aggregation_level=1
        )
        print(f"✓ Created LOM General metadata: {lom.id}")

        # Create LOM Lifecycle
        lifecycle = LOMLifeCycle.objects.create(
            lom_general=lom,
            version="1.0",
            status='draft'
        )
        print(f"✓ Created LOM Lifecycle: {lifecycle.id}")

        # Create LOM Contributor
        contributor = LOMContributor.objects.create(
            lifecycle=lifecycle,
            role='author',
            entity='Universidad Nacional de Chimborazo',
        )
        print(f"✓ Created LOM Contributor: {contributor.id}")

        # Create LOM Educational
        educational = LOMEducational.objects.create(
            lom_general=lom,
            interactivity_type='expositive',
            learning_resource_type='narrative_text',
            interactivity_level='medium',
            semantic_density='medium',
            intended_end_user_role='learner',
            context='higher_education',
            typical_age_range='18+',
            difficulty='medium',
            typical_learning_time='PT30M',
            description='Recurso para aprender sobre el patrimonio cultural de Riobamba',
            language='es'
        )
        print(f"✓ Created LOM Educational: {educational.id}")

        # Create LOM Rights
        rights = LOMRights.objects.create(
            lom_general=lom,
            cost=False,
            copyright_and_other_restrictions=True,
            description='Licencia Creative Commons BY-SA 4.0'
        )
        print(f"✓ Created LOM Rights: {rights.id}")

        # Create LOM Classification
        classification = LOMClassification.objects.create(
            lom_general=lom,
            purpose='discipline',
            taxon_source='UNESCO Classification',
            taxon_id='5.03',
            taxon_entry='Cultural Heritage',
            description='Patrimonio cultural arquitectónico',
            keywords='arquitectura, patrimonio, cultura'
        )
        print(f"✓ Created LOM Classification: {classification.id}")

    # Test retrieval
    print("\n--- Testing Retrieval ---")
    lom_retrieved = LOMGeneral.objects.select_related(
        'heritage_item', 'lifecycle', 'educational', 'rights'
    ).prefetch_related('classifications', 'lifecycle__contributors').get(id=lom.id)

    print(f"✓ Retrieved LOM: {lom_retrieved.title}")
    print(f"  - Heritage Item: {lom_retrieved.heritage_item.title}")
    print(f"  - Language: {lom_retrieved.language}")
    print(f"  - Aggregation Level: {lom_retrieved.aggregation_level}")

    if hasattr(lom_retrieved, 'lifecycle'):
        print(f"  - Lifecycle Status: {lom_retrieved.lifecycle.status}")
        print(f"  - Contributors: {lom_retrieved.lifecycle.contributors.count()}")

    if hasattr(lom_retrieved, 'educational'):
        print(f"  - Learning Resource Type: {lom_retrieved.educational.learning_resource_type}")
        print(f"  - Context: {lom_retrieved.educational.context}")
        print(f"  - Difficulty: {lom_retrieved.educational.difficulty}")

    if hasattr(lom_retrieved, 'rights'):
        print(f"  - Cost: {lom_retrieved.rights.cost}")
        print(f"  - Copyright: {lom_retrieved.rights.copyright_and_other_restrictions}")

    classifications = lom_retrieved.classifications.all()
    print(f"  - Classifications: {classifications.count()}")
    for c in classifications:
        print(f"    * {c.purpose}: {c.taxon_entry}")

    print("\n✅ All tests passed!")
    return True

if __name__ == '__main__':
    try:
        test_lom_creation()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
