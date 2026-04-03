import requests
import json

SORCERY_CATEGORY_ID = 77


def get_sorcery_groups():
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/groups"
    response = requests.get(url)
    data = response.json()
    return data["results"]


def get_products(group_id):
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/{group_id}/products"
    response = requests.get(url)
    data = response.json()
    return data["results"]


def get_prices(group_id):
    url = f"https://tcgcsv.com/tcgplayer/{SORCERY_CATEGORY_ID}/{group_id}/prices"
    response = requests.get(url)
    data = response.json()
    return data["results"]


if __name__ == "__main__":
    ALPHA_GROUP_ID = 23335
    products = get_products(ALPHA_GROUP_ID)
    
    for card in products:
        ext = {d["name"]: d["value"] for d in card["extendedData"]}
        if ext.get("CardType") == "Minion":
            print(json.dumps(card, indent=2))
            break
            