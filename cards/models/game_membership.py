from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import superuser_only


class GameMembership(models.Model, AliveMixin):
    """A player's membership in a game with their role."""

    class Role(models.TextChoices):
        PLAYER = "player", "Player"
        KEEPER = "keeper", "Keeper"

    alive = AliveConf(
        fields=("player", "game", "role"),
        editable_fields=("player", "game", "role"),
        visible_to=superuser_only,
    )

    player = models.ForeignKey(
        "Player",
        on_delete=models.CASCADE,
        related_name="game_memberships",
    )
    game = models.ForeignKey(
        "Game",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PLAYER,
    )

    class Meta:
        unique_together = [["player", "game"]]

    def __str__(self):
        return f"{self.player} - {self.game} ({self.role})"
