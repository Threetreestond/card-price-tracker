import sqlite3

from database import (
    add_card_to_deck,
    decrement_card_in_deck,
    delete_deck,
    get_deck,
    get_deck_cards,
    remove_card_from_deck,
    save_deck,
)
from exceptions import DeckError

class Deck:
    """
    Represents a Sorcery deck. Handles both in-memory state and
    database persistence. A deck has multiple zones:
    - maindeck: spells (minimum 60 cards)
    - sitedeck: sites (minimum 30 cards)
    - collection: any card type (maximum 10 cards)
    - avatar: starting avatar (1 card)
    - maybeboard: cards being considered for the deck

    self.cards stores {(product_id, zone): quantity} so the same card
    can appear in multiple zones (e.g. maindeck and collection).
    """

    def __init__(self, name: str | None = None, deck_id: int | None = None) -> None:
        # name is optional — load() will populate it when loading by deck_id
        self.name = name
        # deck_id is None until save() is called for the first time
        self.deck_id = deck_id
        # Tuple key {(product_id, zone): quantity} — supports same card in multiple zones
        self.cards:dict[tuple[int,str], int] = {}

    def add_card(self, conn:sqlite3.Connection, product_id: int, zone: str, quantity:int = 1) -> None:
        """
        Adds a card to the deck in the specified zone.
        If the deck hasn't been saved yet, saves it first to get a deck_id.
        If the card already exists in that zone, increments the quantity.
        Updates both the database and in-memory state.
        """
        # Auto-save if this deck doesn't have a database ID yet
        if self.deck_id is None:
            self.save(conn)

        add_card_to_deck(conn, self.deck_id, product_id, zone, quantity)

        # Update in-memory state to match database
        key = (product_id, zone)
        if key in self.cards:
            self.cards[key] += quantity
        else:
            self.cards[key] = quantity

    def remove_card(self, conn: sqlite3.Connection, product_id: int, zone: str) -> None:
        """
        Removes a card entirely from the specified zone.
        Updates both the database and in-memory state.
        """
        if self.deck_id is None:
            raise DeckError("Cannot remove a card from an unsaved deck")
        remove_card_from_deck(conn, self.deck_id, product_id, zone)

        # Remove from in-memory state if present
        key = (product_id, zone)
        if key in self.cards:
            del self.cards[key]


    def decrement_card(self, conn: sqlite3.Connection, product_id: int, zone: str, quantity: int = 1) -> None:
        if self.deck_id is None:
            raise DeckError("Cannot decrement a card from an unsaved deck")
        decrement_card_in_deck(conn, self.deck_id, product_id, zone, quantity)

        key = (product_id, zone)
        if key in self.cards:
            if self.cards[key] - quantity <= 0:
                del self.cards[key]
            else:
                self.cards[key] -= quantity

    def save(self, conn: sqlite3.Connection) -> None:
        """
        Saves the deck to the database if it hasn't been saved yet.
        Stores the returned AUTOINCREMENT id in self.deck_id for future use.
        """
        if self.deck_id is None:
            self.deck_id = save_deck(conn, self)

    def load(self, conn: sqlite3.Connection) -> None:
        """
        Loads deck name and card list from the database into memory.
        Populates self.name from the decks table.
        Populates self.cards as {(product_id, zone): quantity} from deck_cards.
        """
        if self.deck_id is None:
            raise DeckError("Cannot load an unsaved deck ")
        # Fetch deck metadata (name, created_at)
        deck_info = get_deck(conn, self.deck_id)
        if deck_info:
            self.name = deck_info["name"]

        # Fetch all cards in this deck and rebuild the in-memory dict
        deck_cards = get_deck_cards(conn, self.deck_id)
        for product_id, quantity, zone in deck_cards:
            self.cards[(product_id, zone)] = quantity

    def delete(self, conn: sqlite3.Connection) -> None:
        if self.deck_id is None:
            raise DeckError("Cannot delete an unsaved deck")
        delete_deck(conn, self.deck_id)



