from database import save_deck, get_deck, add_card_to_deck, remove_card_from_deck

class Deck:
    def __init__(self, name, deck_id=None):
        self.name = name
        self.deck_id = deck_id
        self.cards = {}
    
    def add_card(self, product_id, quantity=1):
        if self.deck_id is None:
            self.save()
        add_card_to_deck(self.deck_id, product_id, quantity)
        if product_id in self.cards:
            self.cards[product_id] += quantity
        else:
            self.cards[product_id] = quantity


    def remove_card(self, product_id):
        pass
    
    def save(self):
        if self.deck_id is None:
            self.deck_id = save_deck(self)
    
    def load(self):
        pass