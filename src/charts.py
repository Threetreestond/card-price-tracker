from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from config import DB_PATH
from context_manager import get_db_connection
from database import get_cards_by_ids

if TYPE_CHECKING:
    from models import Deck


def get_deck_card_data(deck: Deck, zone: str | None = None) -> list[tuple[sqlite3.Row, int]]:
    # get all product_ids from the deck
    # could have used list comprehension:
    # valid_ids = [(pid, qty) for (pid, czone), qty in deck.cards.items() if zone is None or czone == zone]
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
    with get_db_connection(DB_PATH) as conn:
        card_lookup = {card["product_id"]: card for card in get_cards_by_ids(conn, pid_list)}
        # return a list of (card, quantity) tuples
        return [(card_lookup[pid], qty) for pid, qty in valid_ids]


def mana_curve(deck: Deck, zone: str = "maindeck") -> None:
    deck_info = get_deck_card_data(deck, zone)
    cost_counts = {str(i): 0 for i in range(11)}
    for card, qty in deck_info:
        if card["cost"] in cost_counts:
            cost_counts[card["cost"]] += qty
    plt.bar(list(cost_counts.keys()), list(cost_counts.values()))
    plt.xlabel("Cost")
    plt.ylabel("Quantity")
    plt.title("Mana Cost")
    plt.show()


def element_distribution(deck: Deck, zone: str = "maindeck") -> None:
    deck_info = get_deck_card_data(deck, zone)
    element_types = {"Fire": 0, "Water": 0, "Earth": 0, "Air": 0, "None": 0}
    for card, qty in deck_info:
        if card["element"] is not None:
            card_elements = card["element"].split(";")
            for element in card_elements:
                element_types[element] += qty
        else:
            element_types["None"] += qty
    data_show = {e: qty for e, qty in element_types.items() if qty > 0}
    plt.pie(list(data_show.values()), labels=list(data_show.keys()))
    plt.show()


def card_type_distribution(deck: Deck, zone: str | None = None) -> None:
    deck_info = get_deck_card_data(deck, zone)
    card_types_counter = {"Artifact": 0, "Aura": 0, "Site": 0, "Magic": 0, "Avatar": 0, "Minion": 0, "None": 0}
    for card, qty in deck_info:
        if card["card_type"] is not None:
            card_types = card["card_type"].split(";")
            for card_type in card_types:
                card_types_counter[card_type] += qty
        else:
            card_types_counter["None"] += qty
    data_show = {e: qty for e, qty in card_types_counter.items() if qty > 0}
    plt.pie(list(data_show.values()), labels=list(data_show.keys()))
    plt.show()
