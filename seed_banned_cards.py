"""
seed_banned_cards.py
Inserts manually-maintained card records for cards banned from TCGPlayer
(and therefore absent from TCGCSV data). These cards exist in Sorcery but
cannot be bought/sold on TCGPlayer, so they'll never appear in a price sync.

Run once from the project root:
    python seed_banned_cards.py

Safe to re-run — uses INSERT OR IGNORE so it won't duplicate records.
"""

import sqlite3
import sys
import os

sys.path.insert(0, "src")
DB_PATH = "data/cards.db"

# Manual card records. product_id values chosen to be safely above the
# current TCGCSV max (678678) to avoid any future collision.
BANNED_CARDS = [
    {
        "product_id": 900001,
        "group_id": 23336,           # Beta
        "category_id": None,
        "name": "Crusade",
        "clean_name": "Crusade",
        "image_url": "https://d27a44hjr9gen3.cloudfront.net/cards/bet-crusade-b-s.png",
        "url": None,
        "rarity": "Unique",
        "description": (
            "You may summon earth minions to affected sites.\n\n"
            "Allied earth minions occupying affected sites have +1 power."
        ),
        "cost": "2",
        "threshold": "EE",           # 2 earth threshold
        "element": "Earth",
        "type_line": "Unique Aura",
        "card_category": "Spell",
        "card_type": "Aura",
        "card_subtype": None,
        "power_rating": None,
        "defense_power": None,
        "life": None,
        "flavor_text": None,
        "foil": 0,
    },
    {
        "product_id": 900002,
        "group_id": 23336,           # Beta
        "category_id": None,
        "name": "Jihad",
        "clean_name": "Jihad",
        "image_url": "https://d27a44hjr9gen3.cloudfront.net/cards/bet-jihad-b-s.png",
        "url": None,
        "rarity": "Unique",
        "description": None,         # rules text unknown — fill in if you have it
        "cost": "2",
        "threshold": "FF",           # 2 fire threshold
        "element": "Fire",
        "type_line": "Unique Aura",
        "card_category": "Spell",
        "card_type": "Aura",
        "card_subtype": None,
        "power_rating": None,
        "defense_power": None,
        "life": None,
        "flavor_text": None,
        "foil": 0,
    },
]


def seed(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inserted = 0
    for card in BANNED_CARDS:
        cursor.execute("""
            INSERT OR IGNORE INTO cards (
                product_id, group_id, category_id, name, clean_name,
                image_url, url, rarity, description, cost, threshold,
                element, type_line, card_category, card_type, card_subtype,
                power_rating, defense_power, life, flavor_text, foil
            ) VALUES (
                :product_id, :group_id, :category_id, :name, :clean_name,
                :image_url, :url, :rarity, :description, :cost, :threshold,
                :element, :type_line, :card_category, :card_type, :card_subtype,
                :power_rating, :defense_power, :life, :flavor_text, :foil
            )
        """, card)
        if cursor.rowcount:
            print(f"  Inserted: {card['clean_name']} (product_id={card['product_id']})")
            inserted += 1
        else:
            print(f"  Already exists: {card['clean_name']} — skipped")

    conn.commit()
    conn.close()
    print(f"\nDone. {inserted} card(s) inserted.")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run from project root.")
        sys.exit(1)
    seed()
