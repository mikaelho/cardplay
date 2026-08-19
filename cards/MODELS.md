# Models

## Game setup (superuser-managed)

- **Player** has a name and superuser flag. Players participate in multiple games.
- **GameTemplate** defines features of a game. Has a name and tags (M2M to Tag).
- **Game** is a single ongoing game with a name, referring to a GameTemplate.
- **GameMembership** links a Player to a Game with a role (PLAYER or KEEPER). Unique per player+game.
- **Tag** is a named label used to group cards on sheets. Used by GameTemplate, Sheet, and CharacterCard.
- **Sheet** belongs to a GameTemplate, defines which tags are available for characters using that template. Tags are ordered via SheetTag.
- **SheetTag** is the ordered through-model between Sheet and Tag (has position).

## Characters and cards

- **Character** has a name, callsign, notes, belongs to a Game, a Player, and a Sheet. Cards are shown inline grouped by tag (ordered by sheet tag position).
- **Card** is a playable card with a name and notes. Linked to characters via CharacterCard.
- **CharacterCard** connects a Character to a Card with a level (1-10), a `level_mod` and an optional Tag. Level is the baseline; `level_mod` is a temporary shift (short-term advantage or disadvantage) that is cleared by hand, never automatically. The current rank is `level + level_mod` clamped to 1-10, and it is that current rank which determines dice bands (bad/fair/good outcome ranges on a d6). Unique per character+card.
- **Hand** is a named collection of CharacterCards belonging to a character.

## Game play

- **Situation** is a scene or encounter in a game. Has a name, notes, type (situation or note), location, and associated CharacterCards. Tracks dice rolls, assignments, and resolution state. Uses a custom template.
- **SituationCard** is an archived snapshot of a card used in a resolved situation — stores name, notes, level, `level_mod`, character name, and whether it was used. Both level values are copied from the CharacterCard at roll time and are independent of it afterwards.
- **HexMap** is a hex-based map for a game. Stores hex terrain, rivers, overlays, barriers, notes, party location, and trail as JSON fields. Uses a custom template.
