import sys
sys.path.insert(0, "src")
from fastapi import FastAPI
from database import get_all_decks, get_cards
from pydantic import BaseModel
from models import Deck


app = FastAPI()


class DeckCreate(BaseModel):
    name: str



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
