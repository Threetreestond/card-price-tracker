from fetcher import get_sorcery_groups, get_products, get_prices
from database import save_cards, create_tables, save_prices

def sync_cards():
    """
    Fetches all Sorcery cards from TCGCSV and saves them to the database.
    Uses INSERT OR IGNORE so existing cards are skipped — safe to run repeatedly.
    Card attributes are flattened from extendedData inside save_cards().
    """
    # Ensure tables exist before writing — safe to call multiple times
    create_tables()
    # Get all Sorcery sets
    groups = get_sorcery_groups()
    # Loop through each set and fetch its cards
    for group in groups:
        cards = get_products(group["groupId"])
        for card in cards:
            save_cards(card)

def sync_prices():
    """
    Fetches today's prices for all Sorcery cards and saves them to the database.
    Each run adds a new dated row — this builds the price history over time.
    Duplicate entries for the same card/date are ignored via the composite
    primary key (product_id, sub_type_name, date_fetched).
    """
    create_tables()
    groups = get_sorcery_groups()
    for group in groups:
        prices = get_prices(group["groupId"])
        for price in prices:
            save_prices(price)


# Run both syncs when this file is executed directly.
if __name__ == "__main__":
    print("Syncing cards...")
    sync_cards()
    print("Syncing prices...")
    sync_prices()
    print("Done")