import sys
sys.path.insert(0, "src")
from fastapi import FastAPI
from database import get_all_decks, get_cards, get_prices, get_deck_with_cards
from pydantic import BaseModel
from models import Deck


app = FastAPI()


class DeckCreate(BaseModel):
    name: str

class CardAdd(BaseModel):
    product_id: int
    zone: str
    quantity: int = 1


@app.get("/")
def root():
    return {"message": "hello"}

# LANDING PAGE

@app.get("/decks")
def get_decks():
    return get_all_decks()

@app.post("/decks")
def create_deck(deck: DeckCreate):
    # deck.name is available here
    new_deck = Deck(name=deck.name)
    new_deck.save()
# plain dict — FastAPI converts this to JSON automatically
    return {"deck_id": new_deck.deck_id, "name": new_deck.name}

@app.delete("/decks/{deck_id}")
def delete_deck(deck_id):
    deck = Deck(deck_id=deck_id)
    deck.delete()
    return {"message": "Deck deleted"}

# CARD PAGES
@app.get("/cards")
def get_cards_endpoint(
    group_id: int | None = None,
    card_type: str | None = None,
    element: str | None = None,
    cost: str | None = None,
    rarity: str | None = None,
    threshold: str | None = None,
    card_category: str | None = None,
    power_rating: int | None = None,
    defense_power: int | None = None,
    foil: bool | None = None,
    product_id: int | None = None
):
    cards = get_cards(
        group_id=group_id,
        card_type=card_type,
        element=element,
        cost=cost,
        rarity=rarity,
        threshold=threshold,
        card_category=card_category,
        power_rating=power_rating,
        defense_power=defense_power,
        foil=foil,
        product_id=product_id
    )
    return [dict(card) for card in cards]

@app.get("/cards/{product_id}/prices")
def get_card_prices(product_id: int, date_from: str | None = None, date_to: str | None = None):
    pricing = get_prices(product_id=product_id, date_from=date_from,date_to=date_to)
    return [dict(price) for price in pricing]

@app.get("/decks/{deck_id}")
def get_deck_cards(deck_id: int):
    return get_deck_with_cards(deck_id=deck_id)

@app.post("/decks/{deck_id}/cards")
def add_card_to_deck_endpoint(deck_id: int, card: CardAdd):
    deck = Deck(deck_id=deck_id)
    deck.add_card(card.product_id, card.zone, card.quantity)
    return {"message": "card added"}

@app.delete("/decks/{deck_id}/cards/{product_id}")
def delete_card_in_deck_endpoint(deck_id: int, product_id: int, zone: str, remove_all: bool = False, quantity: int = 1):
    deck = Deck(deck_id=deck_id)
    if remove_all:
        deck.remove_card(product_id,zone)
        return {"message": "removed all copies"}
    else:
        deck.decrement_card(product_id, zone, quantity)
        return {"message": "card removed"}