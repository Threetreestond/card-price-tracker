from __future__ import annotations

import sqlite3
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Deck

# Path to the SQLite database file. Defined once here so all functions
# use the same location — change this in one place if the path moves.
DB_PATH = "data/cards.db"


def create_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            product_id INTEGER PRIMARY KEY,
            group_id INTEGER,
            category_id INTEGER,
            name TEXT,
            clean_name TEXT,
            image_url TEXT,
            url TEXT,
            rarity TEXT,
            description TEXT,
            cost TEXT,
            threshold TEXT,
            element TEXT,
            type_line TEXT,
            card_category TEXT,
            card_type TEXT,
            card_subtype TEXT,
            power_rating INTEGER,
            defense_power INTEGER,
            life INTEGER,
            flavor_text TEXT,
            foil INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            product_id INTEGER,
            sub_type_name TEXT,
            low_price REAL,
            mid_price REAL,
            high_price REAL,
            market_price REAL,
            date_fetched TEXT,
            PRIMARY KEY (product_id, sub_type_name, date_fetched)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (
            deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deck_cards (
            deck_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            zone TEXT,
            PRIMARY KEY (deck_id, product_id, zone)
        )
    """)


def save_cards(conn: sqlite3.Connection, card: dict) -> None:
    ext = {d["name"]: d["value"] for d in card["extendedData"]}
    is_foil = "(Foil)" in card["name"]
    foil_int = 1 if is_foil else 0
    conn.execute(
        """
        INSERT OR IGNORE INTO cards (
            product_id, group_id, category_id, name, clean_name,
            image_url, url, rarity, description, cost, threshold,
            element, type_line, card_category, card_type, card_subtype,
            power_rating, defense_power, life, flavor_text, foil
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            card["productId"],
            card["groupId"],
            card["categoryId"],
            card["name"],
            card["cleanName"],
            card["imageUrl"],
            card["url"],
            ext.get("Rarity"),
            ext.get("Description"),
            ext.get("Cost"),
            ext.get("Threshold"),
            ext.get("Element"),
            ext.get("Type Line"),
            ext.get("CardCategory"),
            ext.get("CardType"),
            ext.get("Card Subtype"),
            ext.get("Power Rating"),
            ext.get("Defense Power"),
            ext.get("Life"),
            ext.get("Flavor Text"),
            foil_int,
        ),
    )


def save_prices(conn: sqlite3.Connection, price: dict) -> None:
    today = str(date.today())
    conn.execute(
        """
        INSERT OR IGNORE INTO prices (
            product_id, sub_type_name, low_price, mid_price,
            high_price, market_price, date_fetched
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            price["productId"],
            price["subTypeName"],
            price["lowPrice"],
            price["midPrice"],
            price["highPrice"],
            price["marketPrice"],
            today,
        ),
    )


def save_deck(conn: sqlite3.Connection, deck: Deck) -> int | None:
    today = str(date.today())
    deck_id = conn.execute("INSERT INTO decks (name, created_at) VALUES (?, ?)", (deck.name, today)).lastrowid
    return deck_id


def get_all_decks(conn: sqlite3.Connection) -> list[dict]:
    """
    Returns all decks with their avatar card image if one exists.
    Joins deck_cards → cards to find the avatar zone card for each deck.
    Used by the landing page to show deck thumbnails.
    N+1 query issue, will refactor in the future
    """
    cursor = conn.cursor()
    # Fetch all decks
    cursor.execute("SELECT * FROM decks ORDER BY created_at DESC")
    decks = [dict(row) for row in cursor.fetchall()]
    # For each deck, find the avatar card image (first card in avatar zone)
    for deck in decks:
        cursor.execute(
            """
            SELECT c.image_url FROM deck_cards dc
            JOIN cards c ON dc.product_id = c.product_id
            WHERE dc.deck_id = ? AND dc.zone = 'avatar'
            LIMIT 1
        """,
            (deck["deck_id"],),
        )
        row = cursor.fetchone()
        # If no avatar found, image_url will be None — frontend shows "?" placeholder
        deck["avatar_image"] = row["image_url"] if row else None
    return decks


def add_card_to_deck(
    conn: sqlite3.Connection, deck_id: int | None, product_id: int, zone: str, quantity: int = 1
) -> int:
    added_card = conn.execute(
        """
        INSERT INTO deck_cards (deck_id, product_id, zone, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (deck_id, product_id, zone)
        DO UPDATE SET quantity = quantity + ?
    """,
        (deck_id, product_id, zone, quantity, quantity),
    ).rowcount
    return added_card


def remove_card_from_deck(conn: sqlite3.Connection, deck_id: int, product_id: int, zone: str) -> int:
    return conn.execute(
        "DELETE FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ?", (deck_id, product_id, zone)
    ).rowcount


def decrement_card_in_deck(
    conn: sqlite3.Connection, deck_id: int | None, product_id: int, zone: str, quantity: int = 1
) -> int:
    """
    Returns 1 if the card was removed entirely, 0 if it was decremented-but-survived 
    OR if it was never in the deck to begin with.
    """
    conn.execute(
        "UPDATE deck_cards SET quantity = quantity - ? WHERE deck_id = ? AND product_id = ? AND zone = ?",
        (quantity, deck_id, product_id, zone),
    )
    removed = conn.execute(
        "DELETE FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ? AND quantity <= 0",
        (deck_id, product_id, zone),
    ).rowcount
    return removed


def get_deck_cards(conn: sqlite3.Connection, deck_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT product_id, quantity, zone FROM deck_cards WHERE deck_id = ?", (deck_id,)).fetchall()


def get_deck(conn: sqlite3.Connection, deck_id: int | None) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,)).fetchone() # type: ignore[no-any-return]


def get_card_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] # type: ignore[no-any-return]


def get_cards(
    conn: sqlite3.Connection,
    group_id: int | None = None,
    card_type: str | None = None,
    element: str | None = None,
    cost: str | None = None,
    rarity: str | None = None,
    threshold: str | None = None,
    card_category: str | None = None,
    power_rating: int | None = None,
    defense_power: int | None = None,
    foil: bool | None = None,
    product_id: int | None = None,
) -> list[sqlite3.Row]:
    """
    Flexible card query with optional filters.
    Base filter excludes sealed products (card_type IS NOT NULL).
    """
    foiled: int | None = None
    if foil is not None:
        foiled = 1 if foil else 0
    query = "SELECT * FROM cards WHERE card_type IS NOT NULL"
    params = []
    filters = [
        ("group_id = ?", group_id),
        ("card_type = ?", card_type),
        ("element = ?", element),
        ("cost = ?", cost),
        ("rarity = ?", rarity),
        ("threshold = ?", threshold),
        ("card_category = ?", card_category),
        ("power_rating = ?", power_rating),
        ("defense_power = ?", defense_power),
        ("foil = ?", foiled),
        ("product_id = ?", product_id),
    ]

    for clause, value in filters:
        if value is not None:
            query += f" AND {clause}"
            params.append(value)
    query += " ORDER BY name ASC"
    return conn.execute(query, params).fetchall()


def get_cards_by_ids(conn: sqlite3.Connection, product_ids: list[int]) -> list[sqlite3.Row]:
    if not product_ids:
        return []
    placeholders = ",".join("?" * len(product_ids))
    query = f"SELECT * FROM cards WHERE product_id IN ({placeholders})"
    return conn.execute(query, product_ids).fetchall()


def get_prices(
    conn: sqlite3.Connection, product_id: int | None = None, date_from: str | None = None, date_to: str | None = None
) -> list[sqlite3.Row]:
    """
    Fetches price history ordered oldest→newest for chart rendering.
    """
    filters = [
        ("product_id = ?", product_id),
        ("date_fetched >= ?", date_from),
        ("date_fetched <= ?", date_to),
    ]

    query = "SELECT * FROM prices WHERE 1=1"
    params = []
    for clause, value in filters:
        if value is not None:
            query += f" AND {clause}"
            params.append(value)
    query += " ORDER BY date_fetched ASC"
    return conn.execute(query, params).fetchall()


def get_latest_price(conn: sqlite3.Connection, product_id: int) -> dict | None:
    """
    Returns the most recent price row for a card.
    Used to show current price alongside card info without fetching full history.
    """
    latest_price = conn.execute(
        "SELECT * FROM prices WHERE product_id = ? ORDER BY date_fetched DESC LIMIT 1", (product_id,)
    ).fetchone()
    return dict(latest_price) if latest_price else None


def delete_deck(conn: sqlite3.Connection, deck_id: int) -> int:
    """
    Delete deck and all its cards.
    Need to fix schema with FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE CASCADE
    """
    conn.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
    return conn.execute("DELETE FROM decks WHERE deck_id = ?", (deck_id,)).rowcount


def get_deck_with_cards(conn: sqlite3.Connection, deck_id: int) -> dict:
    """
    Returns deck metadata plus all cards with full details.
    Uses a JOIN to get card attributes alongside zone/quantity from deck_cards.
    Also fetches the latest price for each card so the frontend can display
    current market price and calculate deck total value.
    N+1 query problem, will refactor in the future
    """
    cursor = conn.cursor()

    # Fetch deck metadata
    cursor.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,))
    deck_info = cursor.fetchone()

    # Fetch all cards in deck joined with full card details
    # group_id lets frontend show set name, image_url for card art display
    cursor.execute(
        """
        SELECT
            dc.product_id, dc.quantity, dc.zone,
            c.name, c.rarity, c.cost, c.element, c.card_type,
            c.card_subtype, c.threshold, c.image_url, c.group_id,
            c.power_rating, c.defense_power, c.life, c.description,
            c.flavor_text, c.type_line, c.foil
        FROM deck_cards dc
        JOIN cards c ON dc.product_id = c.product_id
        WHERE dc.deck_id = ?
        ORDER BY dc.zone, c.cost, c.name
    """,
        (deck_id,),
    )
    card_rows = cursor.fetchall()

    # Fetch latest price for each unique product_id in the deck
    # Returns {product_id: {market_price, low_price, ...}}
    product_ids = list({row["product_id"] for row in card_rows})
    price_map = {}
    for pid in product_ids:
        cursor.execute(
            """
            SELECT market_price, low_price, high_price, sub_type_name
            FROM prices WHERE product_id = ?
            ORDER BY date_fetched DESC LIMIT 1
        """,
            (pid,),
        )
        price_row = cursor.fetchone()
        price_map[pid] = dict(price_row) if price_row else {}

    # Attach latest price to each card row
    cards = []
    for row in card_rows:
        card = dict(row)
        card["latest_price"] = price_map.get(card["product_id"], {})
        cards.append(card)

    return {
        "deck": {"deck_id": deck_info["deck_id"], "name": deck_info["name"], "created": deck_info["created_at"]},
        "cards": cards,
    }



