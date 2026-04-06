import sys
sys.path.insert(0, "src")
from fastapi import FastAPI
from database import get_all_decks
from pydantic import BaseModel
from models import Deck


app = FastAPI()


class DeckCreate(BaseModel):
    name: str



@app.get("/")
def root():
    return {"message": "hello"}

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