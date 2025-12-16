import os
import django
import sys

# Add the project root to python path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.education.models import LOMEducational

def fix_tags():
    count = 0
    # Find educational objects marked as document
    edus = LOMEducational.objects.filter(learning_resource_type='document')

    print(f"Checking {edus.count()} items marked as 'document'...")

    for edu in edus:
        # Access the heritage item via lom_general
        try:
             # lom_general matches heritage_item one-to-one
            item = edu.lom_general.heritage_item
            
            # Check documents
            if item.documents.exists():
                first_doc = item.documents.first()
                # Check for narrative text signatures
                is_narrative = (
                    (first_doc.mime_type == 'text/html') or 
                    (first_doc.file and first_doc.file.name.endswith('narrative_text.html')) or
                    (first_doc.file and 'narrative_text' in first_doc.file.name)
                )
                
                if is_narrative:
                    print(f"Fixing item '{item.title}' ({item.id}) - changing type from 'document' to 'narrative_text'")
                    edu.learning_resource_type = 'narrative_text'
                    edu.save()
                    count += 1
        except Exception as e:
            print(f"Error checking item {edu.id}: {e}")

    print(f"Successfully fixed {count} items.")

if __name__ == "__main__":
    fix_tags()
