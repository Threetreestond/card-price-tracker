from database import save_deck, add_card_to_deck, remove_card_from_deck, get_deck_cards

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
        if self.deck_id is None:
            self.save()
        
        remove_card_from_deck(self.deck_id, product_id)
        if product_id in self.cards:
            del self.cards[product_id]
    
    def save(self):
        if self.deck_id is None:
            self.deck_id = save_deck(self)
    
    def load(self):
        deck_cards = get_deck_cards(self.deck_id)
        for product_id, quantity in deck_cards:
            self.cards[product_id] = quantity