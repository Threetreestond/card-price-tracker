from database import save_deck, add_card_to_deck, remove_card_from_deck, get_deck_cards, get_deck

class Deck:
    def __init__(self, name=None, deck_id=None):
        self.name = name
        self.deck_id = deck_id
        self.cards = {}
    
    def add_card(self, product_id, zone, quantity=1):
        if self.deck_id is None:
            self.save()
        add_card_to_deck(self.deck_id, product_id, zone, quantity)
        key = (product_id, zone)
        if key in self.cards:
            self.cards[key] += quantity
        else:
            self.cards[key] = quantity


    def remove_card(self, product_id, zone):
        if self.deck_id is None:
            self.save()
        
        remove_card_from_deck(self.deck_id, product_id, zone)
        key = (product_id, zone)
        if key in self.cards:
            del self.cards[key]
    
    def save(self):
        if self.deck_id is None:
            self.deck_id = save_deck(self)
    
    def load(self):
        deck_info = get_deck(self.deck_id)
        if deck_info:
            self.name = deck_info['name']
        deck_cards = get_deck_cards(self.deck_id)
        for product_id, quantity, zone in deck_cards:
            self.cards[product_id, zone] = quantity


if __name__ == "__main__":
    from database import create_tables
    create_tables()
    
    # create a new deck and add some cards
    deck = Deck(name="Test Water Deck")
    deck.add_card(521503, "MainDeck")  # Accursed Albatross
    deck.add_card(521503, "Collection")  # add another copy
    deck.add_card(521514, "MainDeck")  # Adept Illusionist
    
    print(f"Deck ID: {deck.deck_id}")
    print(f"Cards in memory: {deck.cards}")
    
    # reload from database
    deck2 = Deck(name="Test Water Deck", deck_id=deck.deck_id)
    deck2.load()
    print(f"Cards after reload: {deck2.cards}")
