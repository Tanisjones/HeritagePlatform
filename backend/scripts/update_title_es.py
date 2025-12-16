
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/jduch/Library/CloudStorage/Dropbox/Projects/HeritagePlatform/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.heritage.models import HeritageItem

def update_title():
    try:
        # Find the item with title "Pending Review Item"
        # Since I know the ID from the URL/logs: 8b806592-64e6-47ce-8c7e-4b24b1a0c4c7
        item_id = "8b806592-64e6-47ce-8c7e-4b24b1a0c4c7"
        item = HeritageItem.objects.get(id=item_id)
        
        print(f"Found item: {item.title} (Status: {item.status})")
        
        # Update title to Spanish
        item.title = "Elemento de Revisión Pendiente"
        # Also update category/type references if I could, but title is the main user complaint.
        # "Test description with media" -> "Descripción de prueba con medios"
        item.description = "Descripción de prueba con medios"
        
        item.save()
        print(f"Updated item to: {item.title}")
        
    except HeritageItem.DoesNotExist:
        print("Item NOT found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_title()
