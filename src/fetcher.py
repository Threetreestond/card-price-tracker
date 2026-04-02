import requests

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

if __name__ == "__main__":
    ALPHA_GROUP_ID = 23335
    products = get_products(ALPHA_GROUP_ID)
    print(f"Total cards fetched: {len(products)}")
    print()
    print("First card:")
    print(products[0])