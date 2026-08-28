import django.db.models.deletion
from django.db import migrations, models


def create_timelines(apps, schema_editor):
    """Create one Timeline per game that already has cards, and repoint the
    cards onto it."""
    TimelineCard = apps.get_model("cards", "TimelineCard")
    Timeline = apps.get_model("cards", "Timeline")
    game_ids = set(
        TimelineCard.objects.values_list("game_id", flat=True).distinct()
    )
    by_game = {}
    for gid in game_ids:
        if gid is None:
            continue
        tl, _ = Timeline.objects.get_or_create(game_id=gid)
        by_game[gid] = tl.pk
    for card in TimelineCard.objects.all():
        card.timeline_id = by_game.get(card.game_id)
        card.save(update_fields=["timeline"])


def reverse_timelines(apps, schema_editor):
    TimelineCard = apps.get_model("cards", "TimelineCard")
    for card in TimelineCard.objects.select_related("timeline").all():
        card.game_id = card.timeline.game_id
        card.save(update_fields=["game"])


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0037_timeline_card"),
    ]

    operations = [
        migrations.CreateModel(
            name="Timeline",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("game", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="timeline", to="cards.game")),
            ],
        ),
        migrations.AddField(
            model_name="timelinecard",
            name="tint",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="timelinecard",
            name="timeline",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cards",
                to="cards.timeline",
            ),
        ),
        migrations.RunPython(create_timelines, reverse_timelines),
        migrations.AlterField(
            model_name="timelinecard",
            name="timeline",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cards",
                to="cards.timeline",
            ),
        ),
        migrations.RemoveField(
            model_name="timelinecard",
            name="game",
        ),
    ]
