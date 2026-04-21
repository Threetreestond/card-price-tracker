import json

import requests

# Category ID for Sorcery: Contested Realm on TCGPlayer/TCGCSV.
# Stored as a constant — if it ever changes, update it in one place only.
SORCERY_CATEGORY_ID = 77


def get_sorcery_groups() -> dict:
    """
    Fetches all Sorcery sets from TCGCSV.
    Returns a list of dicts with keys: groupId, name, abbreviation, publishedOn.
    """
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/groups"
    response = requests.get(url)
    data = response.json()
    return data["results"]


def get_products(group_id: int) -> dict:
    """
    Fetches all products (cards, sealed, decks) for a given set.
    Card attributes like rarity and cost are nested inside 'extendedData'
    as key-value pairs — these get flattened when saved to the database.
    """
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/{group_id}/products"
    response = requests.get(url)
    data = response.json()
    return data["results"]


def get_prices(group_id: int) -> dict:
    """
    Fetches current market prices for all products in a given set.
    TCGCSV updates prices daily at approximately 20:00 UTC.
    """
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/{group_id}/prices"
    response = requests.get(url)
    data = response.json()
    return data["results"]


# Only runs when this file is executed directly — used for manual testing.
if __name__ == "__main__":
    ALPHA_GROUP_ID = 23335
    products = get_products(ALPHA_GROUP_ID)

    # Dictionary comprehension flattens extendedData list into {name: value}
    # so attributes can be looked up by name rather than searching the list.
    for card in products:
        ext = {d["name"]: d["value"] for d in card["extendedData"]}
        if ext.get("CardType") == "Minion":
            print(json.dumps(card, indent=2))
            break
