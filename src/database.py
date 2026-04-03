import sqlite3
import os
from datetime import date

DB_PATH = "data/cards.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

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
            PRIMARY KEY (deck_id, product_id)
        )
    """)

    conn.commit()
    conn.close()


'''
breakdown of which columns use extData
product_id,
group_id,
category_id,
name,
clean_name,
image_url,
url,
rarity, -extData "Rarity"
description, -extData "Description"
cost, -extData "Cost"
threshold, -extData "Threshold"
element, -extData "Element"
type_line, -extData "Type Line"
card_category, -extData "CardCategory"
card_type, -extData "CardType"
card_subtype, -extData "Card Subtype"
power_rating, -extData "Power Rating"
defense_power, -extData "Defense Power"
life, -extData "Life"
flavor_text -extData "Flavor Text"
foil - determined by name contains '(Foil)'
'''

def save_cards(card):

    ext = {d["name"]: d["value"] for d in card["extendedData"]}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO cards (
            product_id,
            group_id,
            category_id,
            name,
            clean_name,
            image_url,
            url,
            rarity,
            description,
            cost,
            threshold,
            element,
            type_line,
            card_category,
            card_type,
            card_subtype,
            power_rating,
            defense_power,
            life,
            flavor_text,
            foil
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (  card["productId"],
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
            '(Foil)' in card["name"]  # evaluates to True/False, stored as 1/0
          ))

    conn.commit()
    conn.close()

def save_prices(price):
    today = str(date.today())  # gives "2026-04-03" formatting
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO prices (
            product_id,
            sub_type_name,
            low_price,
            mid_price,
            high_price,
            market_price,
            date_fetched   
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    
    """, (  price["productId"],
            price["subTypeName"],
            price["lowPrice"],
            price["midPrice"],
            price["highPrice"],
            price["marketPrice"],
            today,
          ))
    
    conn.commit()
    conn.close()

def get_card_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cards")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_cards(group_id=None, card_type=None, element=None, cost=None, rarity=None, threshold=None, card_category=None, power_rating=None, defense_power=None, foil=None):
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
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_prices(product_id=None, date_from=None, date_to=None):
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

    query+= " ORDER BY date_fetched ASC"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    create_tables()
    # print(f"Cards in database: {get_card_count()}")
    
    # conn = get_connection()
    # cursor = conn.cursor()
    # cursor.execute("SELECT product_id, name, rarity, cost, threshold FROM cards LIMIT 5")
    # rows = cursor.fetchall()
    # cursor.execute("SELECT COUNT(*) FROM prices")
    # price_rows = cursor.fetchone()[0]
    # conn.close()
    
    # for row in rows:
    #     print(row)
    # print(price_rows)

    # cards = get_cards(group_id=23335, element="Water", card_type="Minion")
    # print(f"Found {len(cards)} cards")
    # for card in cards[:5]:
    #     print(card)

    # cards = get_cards(cost=0)
    # print(f"Found {len(cards)} cards")

    # cards = get_cards(foil=True)
    # print(f"Foil cards: {len(cards)}")
    # cards = get_cards(foil=False)
    # print(f"Non-foil cards: {len(cards)}")

    prices = get_prices(product_id=521503)
    print(f"Price rows for Accursed Albatross: {len(prices)}")
    for price in prices:
        print(price)
