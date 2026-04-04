import sqlite3
import os
from datetime import date

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
    """
    Creates all database tables if they don't already exist.
    Safe to call multiple times — IF NOT EXISTS prevents duplicate creation.
    Called at app startup to ensure the database is always ready.

    Tables:
    - cards: one row per card product (including foils as separate rows)
    - prices: price history — new rows added daily, never overwritten
    - decks: saved deck metadata (name, created date)
    - deck_cards: which cards belong to which deck, in which zone and quantity
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Cards table — stores all Sorcery card data fetched from TCGCSV.
    # cost is TEXT not INTEGER because some cards have cost 'X' (variable cost).
    # foil is stored as INTEGER (0 or 1) — SQLite has no native boolean type.
    # card_type IS NOT NULL is used in queries to filter out sealed products
    # which have no card attributes.
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

    # Prices table — builds price history over time.
    # Composite primary key (product_id, sub_type_name, date_fetched) means
    # the same card can have multiple price rows (Normal vs Foil printings)
    # and a new row is added each day, but duplicates for the same day are ignored.
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

    # Decks table — stores saved deck metadata.
    # deck_id uses AUTOINCREMENT so SQLite assigns the next available integer
    # automatically when a new deck is created.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (
            deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT
        )
    """)

    # Deck cards table — junction table linking decks to cards.
    # Composite primary key (deck_id, product_id, zone) means the same card
    # can appear in multiple zones within the same deck (e.g. maindeck and collection).
    # Valid zones: maindeck, sitedeck, collection, avatar, maybeboard
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


'''
Column source reference — which columns come from extendedData vs top-level:
product_id      - top level
group_id        - top level
category_id     - top level
name            - top level
clean_name      - top level (special chars removed)
image_url       - top level
url             - top level
rarity          - extData "Rarity"
description     - extData "Description"
cost            - extData "Cost"
threshold       - extData "Threshold"
element         - extData "Element"
type_line       - extData "Type Line"
card_category   - extData "CardCategory"
card_type       - extData "CardType"
card_subtype    - extData "Card Subtype"
power_rating    - extData "Power Rating"
defense_power   - extData "Defense Power"
life            - extData "Life"
flavor_text     - extData "Flavor Text"
foil            - derived: True if '(Foil)' in card name
'''


def save_cards(card):
    """
    Saves a single card product to the database.
    Uses INSERT OR IGNORE — if a card with this product_id already exists,
    the insert is silently skipped. Safe to call repeatedly.

    extendedData arrives as a list of {name, displayName, value} dicts.
    The dictionary comprehension flattens this into {name: value} so
    attributes can be looked up by name. ext.get() is used instead of
    ext[] to safely return None for attributes that don't exist on all cards
    (e.g. Life and Defense Power only exist on Minion cards).
    """
    # Flatten extendedData list into a simple {attribute_name: value} dict
    ext = {d["name"]: d["value"] for d in card["extendedData"]}

    conn = get_connection()
    cursor = conn.cursor()

    # Parameterised query — values are passed as a tuple, never interpolated
    # into the SQL string directly. This prevents SQL injection vulnerabilities.
    cursor.execute("""
        INSERT OR IGNORE INTO cards (
            product_id, group_id, category_id, name, clean_name,
            image_url, url, rarity, description, cost, threshold,
            element, type_line, card_category, card_type, card_subtype,
            power_rating, defense_power, life, flavor_text, foil
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
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
        '(Foil)' in card["name"]  # True/False evaluates to 1/0 in SQLite
    ))

    conn.commit()
    conn.close()


def save_prices(price):
    """
    Saves a single price row to the database with today's date.
    The composite primary key (product_id, sub_type_name, date_fetched)
    prevents duplicate entries if sync is run more than once in a day.
    Each daily run builds up the price history used for charts.
    date is evaluated inside the function so it reflects the actual
    current date rather than the date the module was imported.
    """
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO prices (
            product_id, sub_type_name, low_price, mid_price,
            high_price, market_price, date_fetched
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        price["productId"],
        price["subTypeName"],
        price["lowPrice"],
        price["midPrice"],
        price["highPrice"],
        price["marketPrice"],
        today,
    ))

    conn.commit()
    conn.close()


def save_deck(deck):
    """
    Inserts a new deck into the decks table and returns its auto-assigned ID.
    cursor.lastrowid retrieves the AUTOINCREMENT id SQLite assigned to the insert.
    This ID is stored in the Deck object so subsequent operations know which
    deck to update.
    """
    today = str(date.today())
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO decks (name, created_at) VALUES (?, ?)
    """, (deck.name, today))

    # lastrowid is a property (no parentheses) that returns the id of the last insert
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deck_id


def add_card_to_deck(deck_id, product_id, zone, quantity=1):
    """
    Adds a card to a deck in the specified zone, or increases quantity if
    the card already exists in that zone.
    ON CONFLICT ... DO UPDATE handles the increment logic in a single query —
    if the (deck_id, product_id, zone) composite key already exists,
    it adds to the existing quantity rather than failing or replacing.
    quantity appears twice in the tuple: once for the initial INSERT value,
    once for the DO UPDATE increment.
    """
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


def remove_card_from_deck(deck_id, product_id, zone):
    """
    Completely removes a card from a specific zone in a deck.
    Deletes the row entirely rather than setting quantity to 0.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM deck_cards WHERE deck_id = ? AND product_id = ? AND zone = ?
    """, (deck_id, product_id, zone))

    conn.commit()
    conn.close()


def get_deck_cards(deck_id):
    """
    Returns all cards in a deck as a list of (product_id, quantity, zone) tuples.
    Used by Deck.load() to rebuild the in-memory cards dictionary.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_id, quantity, zone FROM deck_cards WHERE deck_id = ?
    """, (deck_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_deck(deck_id):
    """
    Returns a single deck row from the decks table by its ID.
    Used by Deck.load() to populate self.name after loading by deck_id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_card_count():
    """
    Returns the total number of rows in the cards table.
    fetchone() returns a single row tuple e.g. (3171,)
    [0] unwraps the count from the tuple into a plain integer.
    """
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
    Flexible card query with optional filters. Only filters that are provided
    are applied — omitting a parameter returns all values for that column.
    
    The query is built dynamically by starting with a base WHERE clause and
    appending AND conditions for each provided filter. Values are collected
    in a list and converted to a tuple for the parameterised query.

    Base filter (card_type IS NOT NULL) excludes sealed products and
    preconstructed decks which have no card attributes.

    Note: cost uses 'is not None' instead of a plain truthiness check
    because cost=0 is a valid filter value and would be falsy otherwise.
    Same applies to foil (False is a valid filter) and product_id (0 is unlikely
    but consistent).
    """
    query = "SELECT * FROM cards WHERE card_type IS NOT NULL"
    params = []

    if group_id:
        query += " AND group_id = ?"
        params.append(group_id)

    if card_type:
        query += " AND card_type = ?"
        params.append(card_type)

    if element:
        query += " AND element = ?"
        params.append(element)

    if cost is not None:
        query += " AND cost = ?"
        params.append(cost)

    if rarity:
        query += " AND rarity = ?"
        params.append(rarity)

    if threshold:
        query += " AND threshold = ?"
        params.append(threshold)

    if card_category:
        query += " AND card_category = ?"
        params.append(card_category)

    if power_rating:
        query += " AND power_rating = ?"
        params.append(power_rating)

    if defense_power:
        query += " AND defense_power = ?"
        params.append(defense_power)

    if foil is not None:
        query += " AND foil = ?"
        params.append(1 if foil else 0)

    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)

    conn = get_connection()
    cursor = conn.cursor()
    # tuple(params) converts the list to a tuple as required by cursor.execute()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_cards_by_ids(product_ids):
    """
    Fetches multiple cards in a single query using SQL IN clause.
    More efficient than calling get_cards() once per card in a loop.
    
    ",".join("?" * len(product_ids)) builds the right number of placeholders
    e.g. for 3 IDs: "?,?,?"
    Used by the deck show command to look up card names for all deck cards at once.
    """
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
    Fetches price history with optional filters.
    WHERE 1=1 is used as a base so AND conditions can always be appended
    consistently, even when no filters are provided.
    date_from and date_to use >= and <= for range queries.
    Results are ordered oldest to newest — natural order for price history charts.
    """
    query = "SELECT * FROM prices WHERE 1=1"
    params = []

    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)

    if date_from:
        query += " AND date_fetched >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date_fetched <= ?"
        params.append(date_to)

    # Always return in chronological order for price history charts
    query += " ORDER BY date_fetched ASC"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    create_tables()
    prices = get_prices(product_id=521503)
    print(f"Price rows for Accursed Albatross: {len(prices)}")
    for price in prices:
        print(price)