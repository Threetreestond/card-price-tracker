import sys
import logging
from contextlib import asynccontextmanager
from datetime import date

sys.path.insert(0, "src")

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import (
    get_all_decks, get_cards, get_prices,
    get_deck_with_cards, get_latest_price, create_tables, get_connection
)
from pydantic import BaseModel
from models import Deck

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Startup price sync ────────────────────────────────────────────────────────
# FastAPI's lifespan context manager runs code before the server starts
# accepting requests (the part before `yield`) and after it shuts down
# (the part after `yield`). We use it to sync today's prices on startup.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on server start. Syncs today's prices if not already done."""
    sync_prices_if_needed()
    yield  # server runs here
    # (nothing needed on shutdown)

def sync_prices_if_needed():
    """
    Checks whether prices have already been fetched today before hitting
    the API. This prevents duplicate network calls if the server restarts
    multiple times in one day.
    """
    create_tables()
    today = str(date.today())

    # Check if we already have prices for today
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM prices WHERE date_fetched = ?", (today,)
    )
    count = cursor.fetchone()[0]
    conn.close()

    if count > 0:
        log.info(f"Prices already synced for {today} ({count} rows). Skipping.")
        return

    log.info(f"No prices found for {today}. Starting price sync...")
    try:
        # Import here so sync errors don't prevent the server starting
        from sync import sync_prices
        sync_prices()
        log.info("Price sync complete.")
    except Exception as e:
        # Log the error but don't crash the server — stale prices are
        # better than no server at all (e.g. if TCGCSV is temporarily down)
        log.error(f"Price sync failed: {e}")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Pydantic models (request body shapes) ────────────────────────────────────

class DeckCreate(BaseModel):
    name: str

class CardAdd(BaseModel):
    product_id: int
    zone: str
    quantity: int = 1

class CuriosaDeckImport(BaseModel):
    curiosa_url: str


# ── Page routes (return HTML) ─────────────────────────────────────────────────

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/deck/{deck_id}")
def deck_page(request: Request, deck_id: int):
    return templates.TemplateResponse(request, "deck.html")

@app.get("/cards-page")
def cards_page(request: Request):
    return templates.TemplateResponse(request, "cards.html")


# ── Deck API endpoints ────────────────────────────────────────────────────────

@app.get("/decks")
def get_decks():
    """Returns all decks with avatar image url for landing page thumbnails."""
    return get_all_decks()

@app.post("/decks")
def create_deck(deck: DeckCreate):
    new_deck = Deck(name=deck.name)
    new_deck.save()
    return {"deck_id": new_deck.deck_id, "name": new_deck.name}

@app.post("/decks/import-curiosa")
def import_curiosa_deck_endpoint(body: CuriosaDeckImport):
    """
    Imports a public Curiosa deck by URL into the local database.
    Calls Curiosa's internal tRPC API to fetch the deck, then matches
    each card to a local product_id via clean_name + set + foil.

    Returns a summary of what was imported and any cards that couldn't
    be matched (so the user knows what to add manually if needed).
    """
    try:
        from curiosa_importer import import_curiosa_deck
        result = import_curiosa_deck(body.curiosa_url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Curiosa import failed: {e}")
        raise HTTPException(status_code=502, detail=f"Curiosa import failed: {e}")

@app.delete("/decks/{deck_id}")
def delete_deck_endpoint(deck_id: int):
    deck = Deck(deck_id=deck_id)
    deck.delete()
    return {"message": "Deck deleted"}

@app.get("/decks/{deck_id}")
def get_deck_endpoint(deck_id: int):
    """Returns deck metadata + all cards with full attributes and latest price."""
    return get_deck_with_cards(deck_id=deck_id)

@app.post("/decks/{deck_id}/cards")
def add_card_to_deck_endpoint(deck_id: int, card: CardAdd):
    deck = Deck(deck_id=deck_id)
    deck.add_card(card.product_id, card.zone, card.quantity)
    return {"message": "card added"}

@app.delete("/decks/{deck_id}/cards/{product_id}")
def delete_card_in_deck_endpoint(
    deck_id: int, product_id: int,
    zone: str, remove_all: bool = False, quantity: int = 1
):
    deck = Deck(deck_id=deck_id)
    if remove_all:
        deck.remove_card(product_id, zone)
        return {"message": "removed all copies"}
    else:
        deck.decrement_card(product_id, zone, quantity)
        return {"message": "card removed"}


# ── Card API endpoints ────────────────────────────────────────────────────────

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
    """Returns cards matching the given filters. All filters optional."""
    cards = get_cards(
        group_id=group_id, card_type=card_type, element=element, cost=cost,
        rarity=rarity, threshold=threshold, card_category=card_category,
        power_rating=power_rating, defense_power=defense_power,
        foil=foil, product_id=product_id
    )
    return [dict(card) for card in cards]

@app.get("/cards/{product_id}/prices")
def get_card_prices(
    product_id: int,
    date_from: str | None = None,
    date_to: str | None = None
):
    """Returns full price history for a card, ordered oldest to newest."""
    pricing = get_prices(product_id=product_id, date_from=date_from, date_to=date_to)
    return [dict(price) for price in pricing]

@app.get("/cards/{product_id}/price")
def get_card_latest_price(product_id: int):
    """Returns only the latest price row for a card. Faster than full history."""
    return get_latest_price(product_id)
