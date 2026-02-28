"""Knights, Myths, and Seers from Mythic Bastionland.

Knights and Myths (pages 26-27): six tables keyed 1-6 (d6), 12 entries each (d12).
Seers (pages 28-171): one per knight, same d6×d12 structure.

Structure:
    KNIGHTS[d6_value] = [12 names]
    MYTHS[d6_value] = [12 names]
    SEERS[d6_value] = [12 names]
"""

KNIGHTS = {
    1: [
        "The True Knight", "The Snare Knight", "The Tourney Knight",
        "The Bloody Knight", "The Moss Knight", "The War Knight",
        "The Willow Knight", "The Gilded Knight", "The Saddle Knight",
        "The Riddle Knight", "The Talon Knight", "The Barbed Knight",
    ],
    2: [
        "The Trail Knight", "The Amber Knight", "The Horde Knight",
        "The Emerald Knight", "The Chain Knight", "The Banner Knight",
        "The Pigeon Knight", "The Shield Knight", "The Whip Knight",
        "The Seal Knight", "The Horn Knight", "The Dove Knight",
    ],
    3: [
        "The Story Knight", "The Turtle Knight", "The Key Knight",
        "The Moat Knight", "The Boulder Knight", "The Tankard Knight",
        "The Owl Knight", "The Hooded Knight", "The Lance Knight",
        "The Questing Knight", "The Ring Knight", "The Forge Knight",
    ],
    4: [
        "The Rune Knight", "The Gallows Knight", "The Tome Knight",
        "The Meteor Knight", "The Gazer Knight", "The Mule Knight",
        "The Halo Knight", "The Iron Knight", "The Mirror Knight",
        "The Dusk Knight", "The Coin Knight", "The Mock Knight",
    ],
    5: [
        "The Mask Knight", "The Bone Knight", "The Salt Knight",
        "The Violet Knight", "The Cosmic Knight", "The Temple Knight",
        "The Fox Knight", "The Gull Knight", "The Magpie Knight",
        "The Reliquary Knight", "The Vulture Knight", "The Free Knight",
    ],
    6: [
        "The Silk Knight", "The Tiger Knight", "The Leaf Knight",
        "The Glass Knight", "The Hive Knight", "The Ghoul Knight",
        "The Weaver Knight", "The Thunder Knight", "The Dust Knight",
        "The Fanged Knight", "The Pearl Knight", "The Rat Knight",
    ],
}

MYTHS = {
    1: [
        "The Plague", "The Wall", "The Shadow",
        "The River", "The Wyvern", "The Goblin",
        "The Forest", "The Child", "The Order",
        "The Dead", "The Underworld", "The Wurm",
    ],
    2: [
        "The Pack", "The Eye", "The Blade",
        "The Legion", "The Imp", "The Troll",
        "The Demon", "The Sea", "The Elf",
        "The Axe", "The Dwarf", "The Tower",
    ],
    3: [
        "The Chariot", "The Desert", "The Mountain",
        "The Star", "The Sun", "The Moon",
        "The Lion", "The Wheel", "The Cudgel",
        "The Lizard", "The Ogre", "The Spider",
    ],
    4: [
        "The Coven", "The Lich", "The Wight",
        "The Spectre", "The Wraith", "The Beast",
        "The Judge", "The Crown", "The Boar",
        "The Eagle", "The Bat", "The Toad",
    ],
    5: [
        "The Colossus", "The Fortress", "The Citadel",
        "The Catacomb", "The Hound", "The Glade",
        "The Tournament", "The Bull", "The Hydra",
        "The Spire", "The Sprite", "The Hole",
    ],
    6: [
        "The Mist", "The Gargoyle", "The Changeling",
        "The Inferno", "The Harp", "The Tree",
        "The Pool", "The Elephant", "The Snail",
        "The Cave", "The Apparatus", "The Rock",
    ],
}

SEERS = {
    1: [
        "The Rotted Seer", "The Swollen Seer", "The Entombed Seer",
        "The Reed Seer", "The Loathed Seer", "The Lost Seer",
        "The Carved Seer", "The Enthroned Seer", "The Jewelled Seer",
        "The Jawbone Seer", "The Veiled Seer", "The Serpent Seer",
    ],
    2: [
        "The Welcomed Seer", "The Dreaming Seer", "The Hanged Seer",
        "The Unnamed Seer", "The Winged Seer", "The Cured Seer",
        "The Frozen Seer", "The Watched Seer", "The Prey Seer",
        "The Drunken Seer", "The Feasting Seer", "The Sunlit Seer",
    ],
    3: [
        "The Silvered Seer", "The Broken Seer", "The Unspoken Seer",
        "The Brazen Seer", "The Weeping Seer", "The Red Seer",
        "The Screaming Seer", "The Endless Seer", "The Shackled Seer",
        "The Buried Seer", "The Spectral Seer", "The Worst Seer",
    ],
    4: [
        "The Drowned Seer", "The Torn Seer", "The Tangled Seer",
        "The Moonlit Seer", "The Stone Seer", "The Green Seer",
        "The Painted Seer", "The Celebrated Seer", "The Giant Seer",
        "The Fungal Seer", "The Map Seer", "The Chance Seer",
    ],
    5: [
        "The Abacus Seer", "The Twilight Seer", "The Bright Seer",
        "The Gut Seer", "The Rose Seer", "The Tapestry Seer",
        "The Needle Seer", "The Floating Seer", "The Lens Seer",
        "The Predator Seer", "The Hymn Seer", "The Roaming Seer",
    ],
    6: [
        "The Crimson Seer", "The Dying Seer", "The Born Seer",
        "The Blossom Seer", "The Skin Seer", "The Paired Seer",
        "The Armoured Seer", "The Dice Seer", "The Purged Seer",
        "The Damned Seer", "The Pain Seer", "The Rising Seer",
    ],
}
