#!/usr/bin/env python
import os
import sys
import json
import django
from django.contrib.auth import get_user_model

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from rest_framework.test import APIClient
from rest_framework import status
from apps.heritage.models import HeritageItem
from apps.education.models import LOMGeneral

def test_lom_download():
    print("--- Starting LOM Download Test ---")
    
    # 1. Setup User (Staff/Teacher)
    User = get_user_model()
    # Ensure username is unique enough or reuse existing
    user, created = User.objects.get_or_create(username='test_teacher_lom', defaults={'email': 'teacher_lom@test.com'})
    user.set_password('password123')
    user.is_staff = True # IsTeacher permission allows staff
    user.save()
    print(f"✓ User setup: {user.username} (staff={user.is_staff})")

    from rest_framework.test import APIRequestFactory, force_authenticate
    from apps.education.views import LOMPackageViewSet

    # 2. Setup Factory
    factory = APIRequestFactory()

    # 3. Get or Create LOM
    lom = LOMGeneral.objects.first()
    if not lom:
        # Need a heritage item first
        item = HeritageItem.objects.first()
        if not item:
             # Create dummy heritage item if needed
             from apps.heritage.models import HeritageType, HeritageCategory
             from django.contrib.gis.geos import Point
             
             ht, _ = HeritageType.objects.get_or_create(name="Tangible", slug="tangible")
             hc, _ = HeritageCategory.objects.get_or_create(name="Architecture", slug="architecture")
             
             item = HeritageItem.objects.create(
                 title="Test Heritage Item",
                 description="Test Description",
                 location=Point(-78.6, -1.6),
                 heritage_type=ht,
                 heritage_category=hc
             )
        
        lom = LOMGeneral.objects.create(
            heritage_item=item,
            title="Test LOM Resource",
            language="es",
            structure="atomic",
            aggregation_level=1,
            description="Test LOM Description"
        )
        print(f"✓ Created new LOM object: {lom.id}")
    else:
        print(f"✓ Using existing LOM object: {lom.id}")

    # 4. Test Download Endpoint
    url = f'/api/v1/education/lom-packages/{lom.id}/download/'
    print(f"→ Requesting: {url}")
    
    request = factory.get(url)
    force_authenticate(request, user=user)
    
    view = LOMPackageViewSet.as_view({'get': 'download'})
    response = view(request, pk=lom.id)
    
    if response.status_code == 200:
        print(f"✓ Response Status: {response.status_code}")
        print(f"✓ Content-Type: {response.get('Content-Type')}")
        print(f"✓ Content-Disposition: {response.get('Content-Disposition')}")
        
        try:
            content = response.content.decode('utf-8')
            data = json.loads(content)
            print("✓ JSON content is valid")
            print(f"  Title: {data.get('title')}")
            print(f"  ID: {data.get('id')}")
            
            # Verify structure matches serializer expectations roughly
            if 'educational' in data and data['educational']:
                print("  ✓ Contains educational metadata:")
                print(json.dumps(data['educational'], indent=4))
            else:
                print("  ⚠ 'educational' field is missing or empty")

            if 'lifecycle' in data and data['lifecycle']:
                print("  ✓ Contains lifecycle metadata:")
                print(json.dumps(data['lifecycle'], indent=4))
            else:
                 print("  ⚠ 'lifecycle' field is missing or empty")

            if 'rights' in data and data['rights']:
                print("  ✓ Contains rights metadata:")
                print(json.dumps(data['rights'], indent=4))
            
            if 'classifications' in data and data['classifications']:
                print(f"  ✓ Contains {len(data['classifications'])} classifications")
                
        except json.JSONDecodeError:
            print("❌ Response content is not valid JSON")
            return False
            
        print("✅ Download test passed successfully!")
        return True
    else:
        print(f"❌ Request failed with status: {response.status_code}")
        print(f"Response: {response.content.decode('utf-8')}")
        return False

if __name__ == '__main__':
    try:
        if test_lom_download():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
