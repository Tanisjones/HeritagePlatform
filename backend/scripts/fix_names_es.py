
import os
import sys

# Setup Django environment
sys.path.append('/Users/jduch/Library/CloudStorage/Dropbox/Projects/HeritagePlatform/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.heritage.models import HeritageItem, HeritageType

def fix_translations():
    # 1. Update all "Pending Review Item" to Spanish
    items = HeritageItem.objects.filter(title="Pending Review Item")
    count = items.count()
    print(f"Found {count} items with title 'Pending Review Item'")
    
    for item in items:
        item.title = "Elemento de Revisión Pendiente"
        item.description = "Descripción de prueba con medios"
        item.save()
        print(f"Updated item {item.id} to Spanish title")

    # 2. Update Heritage Types if needed
    try:
        intangible = HeritageType.objects.get(slug="intangible")
        if intangible.name != "Inmaterial":
            print(f"Updating HeritageType 'intangible' from '{intangible.name}' to 'Inmaterial'")
            intangible.name = "Inmaterial"
            intangible.save()
            
        tangible = HeritageType.objects.get(slug="tangible")
        # 'Tangible' is fine in Spanish, but let's confirm.
        print(f"HeritageType 'tangible' name is '{tangible.name}'")
        
    except HeritageType.DoesNotExist:
        print("HeritageTypes not found")

if __name__ == "__main__":
    fix_translations()
