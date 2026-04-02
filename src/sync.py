from fetcher import get_sorcery_groups, get_products
from database import save_cards, create_tables

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