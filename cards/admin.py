"""Admin configuration for cards."""

from django.contrib import admin
from .models import Tag, GameTemplate, Game, Player, Sheet, Character, Card, CharacterCard, GameMembership, Situation, Hand, KeeperNote


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(GameTemplate)
class GameTemplateAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'template']
    list_filter = ['template']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Sheet)
class SheetAdmin(admin.ModelAdmin):
    list_display = ['name', 'template']
    list_filter = ['template']


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['name', 'game', 'player', 'sheet']
    list_filter = ['game', 'player', 'sheet']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(CharacterCard)
class CharacterCardAdmin(admin.ModelAdmin):
    list_display = ['character', 'card', 'level', 'tag']
    list_filter = ['character', 'card', 'level', 'tag']


@admin.register(GameMembership)
class GameMembershipAdmin(admin.ModelAdmin):
    list_display = ['player', 'game', 'role']
    list_filter = ['game', 'role']


@admin.register(Situation)
class SituationAdmin(admin.ModelAdmin):
    list_display = ['name', 'game']
    list_filter = ['game']


@admin.register(Hand)
class HandAdmin(admin.ModelAdmin):
    list_display = ['name', 'character', 'draw_active']
    list_filter = ['character']
    list_editable = ['draw_active']


@admin.register(KeeperNote)
class KeeperNoteAdmin(admin.ModelAdmin):
    list_display = ['name', 'game']
    list_filter = ['game']
