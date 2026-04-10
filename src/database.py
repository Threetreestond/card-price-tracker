import sqlite3
import os
from datetime import date
from context_manager import get_db_connection
# Path to the SQLite database file. Defined once here so all functions
# use the same location — change this in one place if the path moves.
DB_PATH = "data/cards.db"


def get_connection():
    """
    Creates and returns a database connection.
    - Creates the data/ directory if it doesn't exist (os.makedirs with exist_ok=True)
    - row_factory = sqlite3.Row means rows are returned as dict-like objects,
      so you can access columns by name (row['name']) instead of position (row[0])
    """
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
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
    conn.commit()
    conn.close()


def save_cards(card):
    ext = {d["name"]: d["value"] for d in card["extendedData"]}
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO cards (
            product_id, group_id, category_id, name, clean_name,
            image_url, url, rarity, description, cost, threshold,
            element, type_line, card_category, card_type, card_subtype,
            power_rating, defense_power, life, flavor_text, foil
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        card["productId"], card["groupId"], card["categoryId"],
        card["name"], card["cleanName"], card["imageUrl"], card["url"],
        ext.get("Rarity"), ext.get("Description"), ext.get("Cost"),
        ext.get("Threshold"), ext.get("Element"), ext.get("Type Line"),
        ext.get("CardCategory"), ext.get("CardType"), ext.get("Card Subtype"),
        ext.get("Power Rating"), ext.get("Defense Power"), ext.get("Life"),
        ext.get("Flavor Text"), '(Foil)' in card["name"]
    ))
    conn.commit()
    conn.close()


def save_prices(price):
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO prices (
            product_id, sub_type_name, low_price, mid_price,
            high_price, market_price, date_fetched
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        price["productId"], price["subTypeName"], price["lowPrice"],
        price["midPrice"], price["highPrice"], price["marketPrice"], today,
    ))
    conn.commit()
    conn.close()


def save_deck(deck):
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO decks (name, created_at) VALUES (?, ?)", (deck.name, today))
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deck_id


def get_all_decks():
    """
    Returns all decks with their avatar card image if one exists.
    Joins deck_cards → cards to find the avatar zone card for each deck.
    Used by the landing page to show deck thumbnails.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Fetch all decks
    cursor.execute("SELECT * FROM decks ORDER BY created_at DESC")
    decks = [dict(row) for row in cursor.fetchall()]
    # For each deck, find the avatar card image (first card in avatar zone)
    for deck in decks:
        cursor.execute("""
            SELECT c.image_url FROM deck_cards dc
            JOIN cards c ON dc.product_id = c.product_id
            WHERE dc.deck_id = ? AND dc.zone = 'avatar'
            LIMIT 1
        """, (deck['deck_id'],))
        row = cursor.fetchone()
        # If no avatar found, image_url will be None — frontend shows "?" placeholder
        deck['avatar_image'] = row['image_url'] if row else None
    conn.close()
    return decks


def add_card_to_deck(deck_id, product_id, zone, quantity=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO deck_cards (deck_id, product_id, zone, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (deck_id, product_id, zone)
        DO UPDATE SET quantity = quantity + ?
    """, (deck_id, product_id, zone, quantity, quantity))
    conn.commit()
    conn.close()


def remove_card_from_deck(conn, deck_id, product_id, zone):
    return conn.execute("DELETE FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ?", (deck_id, product_id, zone)).rowcount



def decrement_card_in_deck(deck_id, product_id, zone, quantity=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE deck_cards SET quantity = quantity - ?
        WHERE deck_id = ? AND product_id = ? AND zone = ?
    """, (quantity, deck_id, product_id, zone))
    cursor.execute("""
        SELECT quantity FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ?
    """, (deck_id, product_id, zone))
    result = cursor.fetchone()
    if result and result['quantity'] <= 0:
        cursor.execute("""
            DELETE FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ?
        """, (deck_id, product_id, zone))
    conn.commit()
    conn.close()


def get_deck_cards(deck_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, quantity, zone FROM deck_cards WHERE deck_id = ?", (deck_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_deck(deck_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_card_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cards")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_cards(group_id=None, card_type=None, element=None, cost=None,
              rarity=None, threshold=None, card_category=None,
              power_rating=None, defense_power=None, foil=None, product_id=None):
    """
    Flexible card query with optional filters.
    Base filter excludes sealed products (card_type IS NOT NULL).
    """
    query = "SELECT * FROM cards WHERE card_type IS NOT NULL"
    params = []
    if group_id:
        query += " AND group_id = ?"; params.append(group_id)
    if card_type:
        query += " AND card_type = ?"; params.append(card_type)
    if element:
        query += " AND element = ?"; params.append(element)
    if cost is not None:
        query += " AND cost = ?"; params.append(cost)
    if rarity:
        query += " AND rarity = ?"; params.append(rarity)
    if threshold:
        query += " AND threshold = ?"; params.append(threshold)
    if card_category:
        query += " AND card_category = ?"; params.append(card_category)
    if power_rating:
        query += " AND power_rating = ?"; params.append(power_rating)
    if defense_power:
        query += " AND defense_power = ?"; params.append(defense_power)
    if foil is not None:
        query += " AND foil = ?"; params.append(1 if foil else 0)
    if product_id is not None:
        query += " AND product_id = ?"; params.append(product_id)
    query += " ORDER BY name ASC"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_cards_by_ids(product_ids):
    placeholders = ",".join("?" * len(product_ids))
    query = f"SELECT * FROM cards WHERE product_id IN ({placeholders})"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(product_ids))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_prices(product_id=None, date_from=None, date_to=None):
    """
    Fetches price history ordered oldest→newest for chart rendering.
    """
    query = "SELECT * FROM prices WHERE 1=1"
    params = []
    if product_id is not None:
        query += " AND product_id = ?"; params.append(product_id)
    if date_from:
        query += " AND date_fetched >= ?"; params.append(date_from)
    if date_to:
        query += " AND date_fetched <= ?"; params.append(date_to)
    query += " ORDER BY date_fetched ASC"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_latest_price(product_id):
    """
    Returns the most recent price row for a card.
    Used to show current price alongside card info without fetching full history.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM prices WHERE product_id = ?
        ORDER BY date_fetched DESC LIMIT 1
    """, (product_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_deck(deck_id):
    """Delete deck and all its cards (deck_cards first to avoid orphaned rows)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
    cursor.execute("DELETE FROM decks WHERE deck_id = ?", (deck_id,))
    conn.commit()
    conn.close()


def get_deck_with_cards(deck_id):
    """
    Returns deck metadata plus all cards with full details.
    Uses a JOIN to get card attributes alongside zone/quantity from deck_cards.
    Also fetches the latest price for each card so the frontend can display
    current market price and calculate deck total value.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch deck metadata
    cursor.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,))
    deck_info = cursor.fetchone()

    # Fetch all cards in deck joined with full card details
    # group_id lets frontend show set name, image_url for card art display
    cursor.execute("""
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
    """, (deck_id,))
    card_rows = cursor.fetchall()

    # Fetch latest price for each unique product_id in the deck
    # Returns {product_id: {market_price, low_price, ...}}
    product_ids = list({row['product_id'] for row in card_rows})
    price_map = {}
    for pid in product_ids:
        cursor.execute("""
            SELECT market_price, low_price, high_price, sub_type_name
            FROM prices WHERE product_id = ?
            ORDER BY date_fetched DESC LIMIT 1
        """, (pid,))
        price_row = cursor.fetchone()
        price_map[pid] = dict(price_row) if price_row else {}

    conn.close()

    # Attach latest price to each card row
    cards = []
    for row in card_rows:
        card = dict(row)
        card['latest_price'] = price_map.get(card['product_id'], {})
        cards.append(card)

    return {
        "deck_id": deck_info["deck_id"],
        "deck_name": deck_info["name"],
        "deck_created": deck_info["created_at"],
        "cards": cards
    }


if __name__ == "__main__":
    # create_tables()
    # prices = get_prices(product_id=521503)
    # print(f"Price rows for Accursed Albatross: {len(prices)}")
    # for price in prices:
    #     print(price)
    with get_db_connection(DB_PATH) as conn:
        returned = remove_card_from_deck(conn, 14, 521503, "maindeck")
        print(returned)
        if returned>0:
            print("Accursed Albatross removed")
        else:
            print("No card removed")