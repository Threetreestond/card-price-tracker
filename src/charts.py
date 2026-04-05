import matplotlib.pyplot as plt
from database import get_cards_by_ids

def get_deck_card_data(deck, zone=None):
    # get all product_ids from the deck
    # could have used list comprehension: valid_ids = [(pid, qty) for (pid, czone), qty in deck.cards.items() if zone is None or czone == zone]
    valid_ids = []
    for (product_id, card_zone), quantity in deck.cards.items():
        # optionally filter by zone
        if zone is not None:
            if card_zone == zone:
                valid_ids.append((product_id, quantity))
        else:
            valid_ids.append((product_id, quantity))

    # list comprehension to extract just product_ids and make a list of them
    pid_list = [pid for pid, qty in valid_ids]
    # fetch full card data using get_cards_by_ids
    card_lookup = {card['product_id']: card for card in get_cards_by_ids(pid_list)}
    # return a list of (card, quantity) tuples
    return [(card_lookup[pid], qty) for pid, qty in valid_ids]

def mana_curve(deck, zone="maindeck"):
    deck_info = get_deck_card_data(deck, zone)
    cost_counts = {str(i): 0 for i in range(11)}
    for card, qty in deck_info:
        if card['cost'] in cost_counts:
            cost_counts[card['cost']] += qty
    plt.bar(cost_counts.keys(), cost_counts.values())
    plt.xlabel("Cost")
    plt.ylabel("Quantity")
    plt.title("Mana Cost")
    plt.show()
    return


def element_distribution(deck, zone="maindeck"):
    deck_info = get_deck_card_data(deck, zone)
    element_types = {"Fire" : 0, "Water" : 0, "Earth" : 0, "Air" : 0, "None" : 0 }
    for card, qty in deck_info:
        if card['element'] is not None:
            card_elements = card['element'].split(";")
            for element in card_elements:
                element_types[element] += qty
        else:
            element_types["None"] += qty
    data_show = {e: qty for e, qty in element_types.items() if qty > 0}
    plt.pie(data_show.values(), labels=data_show.keys())
    plt.show()


if __name__ == "__main__":
    from database import create_tables
    from models import Deck
    create_tables()

    deck = Deck(deck_id=1)
    deck.load()

    data = get_deck_card_data(deck, zone='maindeck')
    for card, quantity in data:
        print(f"{card['name']} x{quantity}")

    mana_curve(deck)
    element_distribution(deck)

