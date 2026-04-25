import logging
import sqlite3

from database import create_tables, save_cards, save_prices
from fetcher import get_prices, get_products, get_sorcery_groups

log = logging.getLogger(__name__)

def sync_cards(conn: sqlite3.Connection) -> None:
    """
    Fetches all Sorcery cards from TCGCSV and saves them to the database.
    Uses INSERT OR IGNORE so existing cards are skipped — safe to run repeatedly.
    Card attributes are flattened from extendedData inside save_cards().
    """
    # Ensure tables exist before writing — safe to call multiple times
    create_tables(conn)
    # Get all Sorcery sets
    groups = get_sorcery_groups()
    # Loop through each set and fetch its cards
    total = 0
    for group in groups:
        cards = get_products(group["groupId"])
        for card in cards:
            save_cards(conn, card)
        total += len(cards)
        log.info("Group %s: %d cards processed", group["groupId"], len(cards))
    log.info("Card sync complete: %d total cards processed", total)    

def sync_prices(conn: sqlite3.Connection) -> None:
    """
    Fetches today's prices for all Sorcery cards and saves them to the database.
    Each run adds a new dated row — this builds the price history over time.
    Duplicate entries for the same card/date are ignored via the composite
    primary key (product_id, sub_type_name, date_fetched).
    """
    create_tables(conn)
    groups = get_sorcery_groups()
    total = 0
    for group in groups:
        prices = get_prices(group["groupId"])
        for price in prices:
            save_prices(conn, price)
        total += len(prices)
        log.info("Group %s: %d prices processed", group["groupId"], len(prices))
    log.info("Price sync complete: %d total prices processed", total)


