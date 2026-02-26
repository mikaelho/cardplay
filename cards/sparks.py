"""Spark Tables from Mythic Bastionland (pages 22-25).

Each page category contains tables with two columns of 12 values each.
Roll 2d12 and combine results for an improvisational prompt.

Structure:
    SPARKS[page_name][table_name] = {
        "columns": (col1_name, col2_name),
        "col1": [12 values],
        "col2": [12 values],
    }
"""

SPARKS = {
    "Nature": {
        "SKY": {
            "columns": ("Tone", "Texture"),
            "col1": [
                "Glittering", "Violet", "Sapphire", "Pale", "Fiery", "Ivory",
                "Slate", "Pink", "Golden", "Bloody", "Bright", "Inky",
            ],
            "col2": [
                "Aurora", "Haze", "Marble", "Glow", "Billows", "Swirl",
                "Streaks", "Dapple", "Rays", "Pillars", "Shimmer", "Swells",
            ],
        },
        "FEATURE": {
            "columns": ("Nature", "Form"),
            "col1": [
                "Buried", "Colourful", "Adorned", "Spiked", "Split", "Entombed",
                "Reflective", "Veiled", "Hot", "Drowned", "Desecrated", "Isolated",
            ],
            "col2": [
                "Brook", "Seat", "Pit", "Cave", "Monolith", "Mound",
                "Cairn", "Pond", "Waterfall", "Spring", "Arch", "Henge",
            ],
        },
        "LAND": {
            "columns": ("Character", "Landscape"),
            "col1": [
                "Barren", "Dry", "Grey", "Sparse", "Sharp", "Teeming",
                "Still", "Soft", "Overgrown", "Vivid", "Sodden", "Lush",
            ],
            "col2": [
                "Marsh", "Heath", "Crags", "Peaks", "Forest", "Valley",
                "Hills", "Meadow", "Bog", "Lakes", "Glades", "Plain",
            ],
        },
        "FLORA": {
            "columns": ("Nature", "Form"),
            "col1": [
                "Aromatic", "Ashen", "Blooming", "Twisted", "Towering", "Fruitful",
                "Stinging", "Vibrant", "Brittle", "Thorny", "Sturdy", "Resinous",
            ],
            "col2": [
                "Grasses", "Heather", "Shrubs", "Brambles", "Canopy", "Ferns",
                "Trunks", "Vines", "Conifers", "Saplings", "Reeds", "Roots",
            ],
        },
        "WATER": {
            "columns": ("Tone", "Texture"),
            "col1": [
                "Crystal", "Teal", "Pearlescent", "Mucky", "Cobalt", "Verdant",
                "Frosted", "Dark", "Verdigris", "Silver", "Emerald", "Jade",
            ],
            "col2": [
                "Silk", "Ripples", "Abyss", "Churn", "Froth", "Mirror",
                "Surge", "Glass", "Surf", "Rapids", "Spray", "Bubbles",
            ],
        },
        "WONDER": {
            "columns": ("Theme", "Element"),
            "col1": [
                "Pleasure", "Secrets", "Prophecy", "Healing", "Desire", "Memory",
                "Death", "Strength", "Temptation", "Pain", "Regret", "Time",
            ],
            "col2": [
                "Light", "Flames", "Stones", "Beasts", "Sparks", "Trails",
                "Mist", "Colours", "Plants", "Wind", "Water", "Shadows",
            ],
        },
        "WEATHER": {
            "columns": ("Description", "Element"),
            "col1": [
                "Gentle", "Fleeting", "Persistent", "Bright", "Thin", "Cool",
                "Hot", "Solid", "Dull", "Faint", "Abundant", "Harsh",
            ],
            "col2": [
                "Rain", "Gusts", "Cloud", "Sunlight", "Mist", "Humidity",
                "Thunder", "Dust", "Warmth", "Drizzle", "Breeze", "Fog",
            ],
        },
        "FAUNA": {
            "columns": ("Nature", "Form"),
            "col1": [
                "Watchful", "Helpful", "Graceful", "Loud", "Mischievous", "Deceitful",
                "Enlightening", "Placid", "Beautiful", "Mighty", "Hostile", "Aloof",
            ],
            "col2": [
                "Ungulates", "Songbirds", "Canines", "Rodents", "Amphibians", "Insects",
                "Felines", "Reptiles", "Hawks", "Mustelids", "Fowl", "Bears",
            ],
        },
        "OTHERWORLD": {
            "columns": ("Character", "Landscape"),
            "col1": [
                "Acidic", "Black", "Smoke", "Frozen", "Dead", "Broken",
                "Colossal", "Living", "Burning", "Sludge", "White", "Sweet",
            ],
            "col2": [
                "Flats", "Labyrinth", "Ruins", "Stairs", "Desert", "Craters",
                "Cavern", "Jungle", "Dunes", "Tunnels", "Island", "Mountain",
            ],
        },
    },
    "Civilisation": {
        "WOE": {
            "columns": ("Description", "Incident"),
            "col1": [
                "Secretive", "Violent", "Looming", "Sudden", "Ongoing", "Prophecised",
                "Mysterious", "Sanctioned", "Unseen", "Vast", "Escalating", "Concealed",
            ],
            "col2": [
                "Disease", "Famine", "Raids", "Invasion", "Abduction", "Storm",
                "Fire", "Revolt", "Exodus", "Beast", "Killing", "Theft",
            ],
        },
        "KEEP": {
            "columns": ("Centrepiece", "Decoration"),
            "col1": [
                "Hearth", "Throne", "Musicians", "Pool", "Advisers", "Servants",
                "Shrine", "Table", "Reliquary", "Cauldron", "Chandelier", "Guards",
            ],
            "col2": [
                "Antlers", "Silver", "Heraldry", "Bones", "Flowers", "Scripture",
                "Jewels", "Wreaths", "Candles", "Fur", "Tapestries", "Shields",
            ],
        },
        "HOLDING": {
            "columns": ("Style", "Feature"),
            "col1": [
                "Dark", "Ruined", "Hostile", "Ancient", "Ornate", "Wild",
                "Pristine", "Fortified", "Unfinished", "Welcoming", "Proud", "Bright",
            ],
            "col2": [
                "Turrets", "Tower", "Wall", "Battlements", "Citadel", "Gate",
                "Spire", "Dome", "Beacons", "Bridge", "Pillars", "Moat",
            ],
        },
        "BAILEY": {
            "columns": ("Style", "Feature"),
            "col1": [
                "Filthy", "Abandoned", "Joyous", "Sophisticated", "Industrious", "Humble",
                "Majestic", "Hallowed", "Rustic", "Solemn", "Bustling", "Immaculate",
            ],
            "col2": [
                "Marketplace", "Forge", "Library", "Fountain", "Temple", "Forum",
                "Tomb", "Garden", "Hall", "Workshops", "Arena", "Garrison",
            ],
        },
        "LUXURIES": {
            "columns": ("Rarity", "Type"),
            "col1": [
                "Antique", "Intricate", "Unique", "Scarce", "Hazardous", "Flawless",
                "Luminous", "Lost", "Esoteric", "Sacred", "Mythical", "Beautiful",
            ],
            "col2": [
                "Jewel", "Wine", "Spice", "Fragrance", "Silk", "Fur",
                "Artwork", "Sword", "Creature", "Ore", "Root", "Scripture",
            ],
        },
        "GOODS": {
            "columns": ("Theme", "Type"),
            "col1": [
                "Military", "Abundant", "Traditional", "Specialist", "Industrious", "Innovative",
                "Secretive", "Simple", "Strong", "Decorated", "Fine", "Lucky",
            ],
            "col2": [
                "Textile", "Livestock", "Grain", "Mead", "Tools", "Stone",
                "Wood", "Pottery", "Metal", "Leather", "Honey", "Herb",
            ],
        },
        "FOOD": {
            "columns": ("Quality", "Type"),
            "col1": [
                "Spiced", "Herbal", "Crunchy", "Sour", "Dry", "Fermented",
                "Salted", "Wet", "Fatty", "Chewy", "Sweet", "Mild",
            ],
            "col2": [
                "Fish", "Fruit", "Stew", "Mushrooms", "Pie", "Cheese",
                "Nuts", "Cake", "Porridge", "Bread", "Vegetable", "Meat",
            ],
        },
        "DRAMA": {
            "columns": ("Theme", "Detail"),
            "col1": [
                "Betrayal", "Jealousy", "Rivalry", "Infidelity", "Coup", "Ambition",
                "Redemption", "Revelation", "Wrath", "Greed", "Banishment", "Manipulation",
            ],
            "col2": [
                "Brawl", "Poison", "Oath", "Feast", "Letters", "Disguise",
                "Inheritance", "Assassin", "Family", "Alcohol", "Blackmail", "Gold",
            ],
        },
        "NEWS": {
            "columns": ("Subject", "Mood"),
            "col1": [
                "Duel", "Birth", "Market", "Trial", "Ritual", "Mercenaries",
                "Festival", "Tournament", "Punishment", "Performance", "Death", "Marriage",
            ],
            "col2": [
                "Pensive", "Joyous", "Content", "Divided", "Furious", "Sceptical",
                "Adoring", "Nostalgic", "Unified", "Bleak", "Solemn", "Optimistic",
            ],
        },
    },
    "People": {
        "PERSONALITY": {
            "columns": ("Demeanour", "Interest"),
            "col1": [
                "Cautious", "Spiritual", "Intellectual", "Ambitious", "Serene", "Righteous",
                "Empathetic", "Unstable", "Prying", "Melancholic", "Cynical", "Rash",
            ],
            "col2": [
                "Botany", "History", "Music", "Gambling", "Animals", "Art",
                "Cookery", "Craft", "Fishing", "Fashion", "Hunting", "Stories",
            ],
        },
        "VOICE": {
            "columns": ("Tone", "Manner"),
            "col1": [
                "Whispering", "Soothing", "Smooth", "Flat", "Mumbled", "Weak",
                "Strong", "Hesitant", "Melodic", "Gravelly", "Erratic", "Booming",
            ],
            "col2": [
                "Formal", "Poetic", "Precise", "Intense", "Rambling", "Detached",
                "Passionate", "Terse", "Relaxed", "Blunt", "Boisterous", "Friendly",
            ],
        },
        "BACKGROUND": {
            "columns": ("Upbringing", "Memory"),
            "col1": [
                "Deprived", "Pious", "Outcast", "Military", "Insular", "Nomadic",
                "Drudgery", "Mercantile", "Feral", "Prestigious", "Academic", "Pampered",
            ],
            "col2": [
                "War", "Migration", "Riding", "Study", "Exile", "Joy",
                "Sickness", "Escape", "Injury", "Friendship", "Execution", "Romance",
            ],
        },
        "AILMENT": {
            "columns": ("Descriptor", "Symptom"),
            "col1": [
                "Hidden", "Mild", "Intermittent", "Growing", "Medicated", "Denied",
                "Unexplained", "Constant", "Diminishing", "Permanent", "Debilitating", "Obvious",
            ],
            "col2": [
                "Insomnia", "Migraines", "Arthritis", "Nausea", "Fixation", "Blindness",
                "Deafness", "Melancholy", "Shaking", "Frailty", "Coughing", "Lethargy",
            ],
        },
        "HERALDRY": {
            "columns": ("Palette", "Symbol"),
            "col1": [
                "Light", "Hot", "Earthy", "Rich", "Metallic", "Brilliant",
                "Grey", "Jewelled", "Subdued", "Airy", "Cold", "Dark",
            ],
            "col2": [
                "Beast", "Bird", "Fish", "Weapon", "Crown", "Tree",
                "Flower", "Bodypart", "Structure", "Ring", "Tool", "Star",
            ],
        },
        "RELATIONSHIP": {
            "columns": ("State", "Connection"),
            "col1": [
                "Adoring", "Reluctant", "Secret", "Estranged", "Hateful", "Distant",
                "Harmonious", "Intimate", "Recent", "Sworn", "Tumultuous", "Resentful",
            ],
            "col2": [
                "Kin", "Friend", "Lover", "Spouse", "Supporter", "Ally",
                "Rival", "Successor", "Mentor", "Peer", "Enemy", "Guardian",
            ],
        },
        "DESIRE": {
            "columns": ("Ambition", "Motive"),
            "col1": [
                "Escape", "Wealth", "Status", "Knowledge", "Mastery", "Heirloom",
                "Marriage", "Truth", "Travel", "Power", "Security", "Forgiveness",
            ],
            "col2": [
                "Freedom", "Love", "Legacy", "Recovery", "Revenge", "Duty",
                "Fear", "Guilt", "Recognition", "Defiance", "Curiosity", "Hatred",
            ],
        },
        "APPEARANCE": {
            "columns": ("Physique", "Dress"),
            "col1": [
                "Delicate", "Short", "Robust", "Hard", "Haggard", "Cold",
                "Warm", "Youthful", "Soft", "Sickly", "Tall", "Rough",
            ],
            "col2": [
                "Armoured", "Tattered", "Vibrant", "Crude", "Eclectic", "Traditional",
                "Comfortable", "Gaudy", "Drab", "Decorated", "Functional", "Elegant",
            ],
        },
        "TASK": {
            "columns": ("Action", "Subject"),
            "col1": [
                "Investigate", "Capture", "Destroy", "Transport", "Retrieve", "Mend",
                "Break", "Guard", "Aid", "Salvage", "Conceal", "Hunt",
            ],
            "col2": [
                "Knight", "Seer", "Vassals", "Livestock", "Monument", "Gold",
                "Ruin", "Animals", "Dwelling", "Holding", "Bridge", "Warband",
            ],
        },
    },
    "Combat": {
        "CONFLICT": {
            "columns": ("Dispute", "Status"),
            "col1": [
                "Border", "Religion", "Succession", "Resource", "Debt", "Betrayal",
                "Theft", "Conquest", "Marriage", "Deceit", "Waterway", "Bloodfeud",
            ],
            "col2": [
                "War", "Raids", "Animosity", "Truce", "Skirmishes", "Standoff",
                "Occupation", "Stalemate", "Blockade", "Tension", "Forgotten", "Negotiations",
            ],
        },
        "SOLDIER": {
            "columns": ("Quality", "Type"),
            "col1": [
                "Mobile", "Reluctant", "Mounted", "Renowned", "Zealous", "Conscript",
                "Cowardly", "Heavy", "Bloodthirsty", "Fancy", "Fearsome", "Mercenary",
            ],
            "col2": [
                "Skirmisher", "Archer", "Scout", "Militia", "Guard", "Infiltrator",
                "Raider", "Veteran", "Infantry", "Rider", "Charger", "Knight",
            ],
        },
        "WEAPON": {
            "columns": ("Descriptor", "Feature"),
            "col1": [
                "Short", "Pole", "Chain", "Barbed", "Forked", "Curved",
                "Weighted", "Double", "Crossed", "Throwing", "Thin", "Long",
            ],
            "col2": [
                "Blade", "Spear", "Axe", "Mace", "Cleaver", "Hammer",
                "Spike", "Hook", "Club", "Rod", "Fang", "Sword",
            ],
        },
        "STRATEGY": {
            "columns": ("Plan", "Twist"),
            "col1": [
                "Encircle", "Capture", "Assault", "Harass", "Pillage", "Outlast",
                "Ambush", "Overwhelm", "Blockade", "Divide", "Focus", "Counter",
            ],
            "col2": [
                "Darkness", "Reserves", "Diversion", "Betrayal", "Artillery", "Camouflage",
                "Bluff", "Delay", "Decoy", "Bait", "Sacrifice", "Fire",
            ],
        },
        "DEPLOYMENT": {
            "columns": ("Style", "Formation"),
            "col1": [
                "Aggressive", "Mobile", "Tight", "Deceptive", "Shielded", "Rigid",
                "Flexible", "Open", "Focused", "Dispersed", "Reinforced", "Defensive",
            ],
            "col2": [
                "Line", "Column", "Chevron", "Ranks", "Square", "Circle",
                "Flank", "Skirmish", "Block", "Square", "Wedge", "Scatter",
            ],
        },
        "BATTLEFIELD": {
            "columns": ("Feature", "Detail"),
            "col1": [
                "River", "Ruins", "Hill", "Forest", "Lake", "Outpost",
                "Pass", "Farm", "Trail", "Bridge", "Wall", "Dwelling",
            ],
            "col2": [
                "Smoke", "Mud", "Flies", "Trenches", "Tower", "Boulders",
                "Flowers", "Streams", "Thorns", "Stink", "Ravine", "Tombs",
            ],
        },
        "EVENT": {
            "columns": ("Subject", "Event"),
            "col1": [
                "Allies", "Morale", "Weather", "Terrain", "Strategy", "Discipline",
                "Animal", "Opportunists", "Deception", "Leader", "Loot", "Weapons",
            ],
            "col2": [
                "Collapse", "Attack", "Slaughter", "Stalemate", "Stall", "Falter",
                "Sabotage", "Scatter", "Charge", "Confusion", "Worsening", "Discovery",
            ],
        },
        "DUEL": {
            "columns": ("Stipulation", "Twist"),
            "col1": [
                "Joust", "Swords", "Partner", "Team", "Unarmoured", "Chained",
                "Blood", "Death", "Surrender", "Judged", "Blunt", "Javelins",
            ],
            "col2": [
                "Timed", "Pit", "Bridge", "Immobile", "Maze", "Archers",
                "Fire", "Beasts", "Mud", "Night", "Water", "Cage",
            ],
        },
        "MANOEUVRES": {
            "columns": ("Action", "Intent"),
            "col1": [
                "Feint", "Strike", "Boast", "Defend", "Negotiate", "Flurry",
                "Rush", "Taunt", "Jab", "Charge", "Onslaught", "Provoke",
            ],
            "col2": [
                "Demoralise", "Confuse", "Exploit", "Stall", "Relocate", "Observe",
                "Defeat", "Expose", "Surprise", "Stagger", "Weaken", "Intimidate",
            ],
        },
    },
}
