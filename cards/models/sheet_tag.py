from django.db import models


class SheetTag(models.Model):
    """Ordered association between a Sheet and a Tag."""

    sheet = models.ForeignKey("Sheet", on_delete=models.CASCADE)
    tag = models.ForeignKey("Tag", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        unique_together = [["sheet", "tag"]]

    def __str__(self):
        return f"{self.sheet} - {self.tag} (pos {self.position})"
