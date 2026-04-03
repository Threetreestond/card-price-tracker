from fetcher import get_sorcery_groups, get_products, get_prices
from database import save_cards, create_tables, save_prices

def sync_cards():
    # ensure tables exist before we try to write to them
    create_tables()
    # fetch all sorcery sets
    groups = get_sorcery_groups()
    # for each set, fetch its products
    for group in groups:
        cards = get_products(group["groupId"])
        # save the products to the database
        for card in cards:
            save_cards(card)

def sync_prices():
    create_tables()
    groups = get_sorcery_groups()
    for group in groups:
        prices = get_prices(group["groupId"])
        for price in prices:
            save_prices(price)


if __name__ == "__main__":
    print("Syncing cards...")
    sync_cards()
    print("Syncing prices...")
    sync_prices()
    print("Done")