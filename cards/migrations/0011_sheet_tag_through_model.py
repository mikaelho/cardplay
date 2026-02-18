# Custom migration: Switch Sheet.tags from auto M2M to explicit SheetTag through model.

import django.db.models.deletion
from django.db import migrations, models


def migrate_sheet_tags(apps, schema_editor):
    """Copy existing M2M data from auto-generated table to SheetTag."""
    SheetTag = apps.get_model('cards', 'SheetTag')
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT sheet_id, tag_id FROM cards_sheet_tags ORDER BY id")
        rows = cursor.fetchall()
    # Group by sheet to assign positions
    by_sheet = {}
    for sheet_id, tag_id in rows:
        by_sheet.setdefault(sheet_id, []).append(tag_id)
    objs = []
    for sheet_id, tag_ids in by_sheet.items():
        for pos, tag_id in enumerate(tag_ids):
            objs.append(SheetTag(sheet_id=sheet_id, tag_id=tag_id, position=pos))
    SheetTag.objects.bulk_create(objs)


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0010_character_callsign'),
    ]

    operations = [
        # 1. Create the new through model table
        migrations.CreateModel(
            name='SheetTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=0)),
                ('sheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cards.sheet')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cards.tag')),
            ],
            options={
                'ordering': ['position'],
                'unique_together': {('sheet', 'tag')},
            },
        ),
        # 2. Copy existing data from auto-generated M2M table
        migrations.RunPython(migrate_sheet_tags, migrations.RunPython.noop),
        # 3. Remove old auto-generated M2M field
        migrations.RemoveField(
            model_name='sheet',
            name='tags',
        ),
        # 4. Add new M2M field with explicit through model
        migrations.AddField(
            model_name='sheet',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='sheets', through='cards.SheetTag', to='cards.tag'),
        ),
    ]
