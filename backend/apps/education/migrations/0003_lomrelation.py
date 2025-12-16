from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('heritage', '0008_backfill_governance_fields'),
        ('education', '0002_resourcecategory_resourcetype_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LOMRelation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('is_part_of', 'Is part of'), ('has_part', 'Has part'), ('is_version_of', 'Is version of'), ('has_version', 'Has version'), ('is_format_of', 'Is format of'), ('has_format', 'Has format'), ('references', 'References'), ('is_referenced_by', 'Is referenced by'), ('is_similar_to', 'Is similar to'), ('requires', 'Requires'), ('is_required_by', 'Is required by')], help_text='Type of relationship', max_length=40, verbose_name='kind')),
                ('target_url', models.URLField(blank=True, help_text='External relation target', verbose_name='target URL')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lom_general', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relations', to='education.lomgeneral', verbose_name='LOM general')),
                ('target_heritage_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lom_relations_targeting_item', to='heritage.heritageitem', verbose_name='target heritage item')),
                ('target_media_file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lom_relations_targeting_media', to='heritage.mediafile', verbose_name='target media file')),
            ],
            options={
                'verbose_name': 'LOM Relation',
                'verbose_name_plural': 'LOM Relations',
                'ordering': ['-updated_at'],
            },
        ),
    ]
