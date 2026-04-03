from database import save_deck, get_deck, add_card_to_deck, remove_card_from_deck

class Deck:
    def __init__(self, name, deck_id=None):
        self.name = name
        self.deck_id = deck_id
        self.cards = []
    
    def add_card(self, product_id, quantity=1):
        pass
    
    def remove_card(self, product_id):
        pass
    
    def save(self):
        pass
    
    def load(self):
        pass