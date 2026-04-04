from database import save_deck, add_card_to_deck, remove_card_from_deck, get_deck_cards, get_deck


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

    def __init__(self, name=None, deck_id=None):
        # name is optional — load() will populate it when loading by deck_id
        self.name = name
        # deck_id is None until save() is called for the first time
        self.deck_id = deck_id
        # Tuple key {(product_id, zone): quantity} — supports same card in multiple zones
        self.cards = {}

    def add_card(self, product_id, zone, quantity=1):
        """
        Adds a card to the deck in the specified zone.
        If the deck hasn't been saved yet, saves it first to get a deck_id.
        If the card already exists in that zone, increments the quantity.
        Updates both the database and in-memory state.
        """
        # Auto-save if this deck doesn't have a database ID yet
        if self.deck_id is None:
            self.save()

        add_card_to_deck(self.deck_id, product_id, zone, quantity)

        # Update in-memory state to match database
        key = (product_id, zone)
        if key in self.cards:
            self.cards[key] += quantity
        else:
            self.cards[key] = quantity

    def remove_card(self, product_id, zone):
        """
        Removes a card entirely from the specified zone.
        Updates both the database and in-memory state.
        """
        if self.deck_id is None:
            self.save()

        remove_card_from_deck(self.deck_id, product_id, zone)

        # Remove from in-memory state if present
        key = (product_id, zone)
        if key in self.cards:
            del self.cards[key]

    def save(self):
        """
        Saves the deck to the database if it hasn't been saved yet.
        Stores the returned AUTOINCREMENT id in self.deck_id for future use.
        """
        if self.deck_id is None:
            self.deck_id = save_deck(self)

    def load(self):
        """
        Loads deck name and card list from the database into memory.
        Populates self.name from the decks table.
        Populates self.cards as {(product_id, zone): quantity} from deck_cards.
        """
        # Fetch deck metadata (name, created_at)
        deck_info = get_deck(self.deck_id)
        if deck_info:
            self.name = deck_info['name']

        # Fetch all cards in this deck and rebuild the in-memory dict
        deck_cards = get_deck_cards(self.deck_id)
        for product_id, quantity, zone in deck_cards:
            self.cards[(product_id, zone)] = quantity


if __name__ == "__main__":
    from database import create_tables
    create_tables()

    deck = Deck(name="Test Water Deck")
    deck.add_card(521503, "maindeck")   # Accursed Albatross
    deck.add_card(521503, "collection") # Same card, different zone
    deck.add_card(521514, "maindeck")   # Adept Illusionist

    print(f"Deck ID: {deck.deck_id}")
    print(f"Cards in memory: {deck.cards}")

    # Reload from database to verify persistence
    deck2 = Deck(deck_id=deck.deck_id)
    deck2.load()
    print(f"Cards after reload: {deck2.cards}")