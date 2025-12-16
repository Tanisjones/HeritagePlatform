from django.db import migrations

def create_notification_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model('notifications', 'NotificationTemplate')
    NotificationTemplate.objects.create(
        name='contribution-published',
        subject='Your contribution has been published',
        body='''
        <html>
        <body>
            <p>Hello,</p>
            <p>Your contribution "{{ heritage_item_title }}" has been published.</p>
            <p>Thank you for your contribution!</p>
        </body>
        </html>
        ''',
        is_html=True,
    )
    NotificationTemplate.objects.create(
        name='contribution-rejected',
        subject='Your contribution has been rejected',
        body='''
        <html>
        <body>
            <p>Hello,</p>
            <p>Your contribution "{{ heritage_item_title }}" has been rejected.</p>
            <p>Moderator feedback: {{ moderator_feedback }}</p>
            <p>If you have any questions, please contact us.</p>
        </body>
        </html>
        ''',
        is_html=True,
    )

class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_notification_templates),
    ]
