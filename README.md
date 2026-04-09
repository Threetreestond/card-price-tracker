# Sorcery: Contested Realm — Card Price Tracker

A personal deck builder and price tracker for the Sorcery: Contested Realm TCG. Built as Phase 1 of a 24-month AI/ML learning roadmap — the goal was to reach Python fluency through a real project rather than tutorials.

## What it does

- Pulls card and price data daily from [TCGCSV](https://tcgcsv.com) (a TCGPlayer mirror — no API key needed)
- Stores ~3,000+ cards and daily price history in a local SQLite database
- Serves a web interface for browsing cards, building decks, and tracking collection value
- Syncs today's prices automatically on server start

## Features

**Landing page**
- Deck grid with avatar card image thumbnails
- Create and delete decks

**Deck editor**
- Tabular card list with Qty / Card / Element / Cost / Rarity / Price columns
- Three-level grouping — e.g. Group by Zone → Set → Rarity, sorted by Cost
- Zone filter tabs (All / Maindeck / Site Deck / Avatar / Collection / Maybeboard)
- Click any card row to open a slide-out panel with full card details, price history sparkline, and TCGPlayer link
- Quick Add — search by name/element/type/rarity
- Browse Cards — full gallery browser with image tiles, filters, and +/- controls directly on tiles
- Price Summary panel with zone checkboxes that also control the mana curve, element distribution, and card type charts

**Card gallery**
- Image grid grouped by card name — one tile per unique card, set count badge
- Filters: set, element, type, rarity, cost
- Sort by name, cost, rarity, or element
- Slide-out panel with set selector to compare prices across printings

## Project structure

```
card-price-tracker/
├── api.py                  ← FastAPI app — routes, startup sync, server entry point
├── src/
│   ├── fetcher.py          ← TCGCSV API calls (groups, products, prizes)
│   ├── database.py         ← SQLite read/write functions
│   ├── sync.py             ← Orchestration: fetch → save cards and prices
│   ├── models.py           ← Deck class (OOP wrapper around database operations)
│   ├── charts.py           ← matplotlib charts (CLI use)
│   └── main.py             ← CLI entry point (argparse)
├── templates/
│   ├── index.html          ← Landing page
│   ├── deck.html           ← Deck editor
│   └── cards.html          ← Card gallery
├── static/
│   ├── css/style.css       ← Main stylesheet
│   ├── css/additions.css   ← Supplementary styles
│   ├── js/main.js          ← Landing page JS
│   ├── js/deck.js          ← Deck editor JS
│   └── js/cards.js         ← Card gallery JS
├── data/
│   └── cards.db            ← SQLite database (gitignored)
├── tests/                  ← pytest test suite
├── requirements.txt
└── README.md
```

## Setup

**1. Clone the repo**
```
git clone https://github.com/Threetreestond/card-price-tracker
cd card-price-tracker
```

**2. Create and activate a virtual environment**
```
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**
```
pip install -r requirements.txt
```

**4. Run the initial card sync** (one-time — downloads ~3,000 cards)
```
python src/sync.py
```

**5. Start the web server**
```
uvicorn api:app --reload
```

Open `http://localhost:8000` in your browser. Prices are synced automatically on each server start (skipped if already fetched today).

## Data source

Card and price data comes from [TCGCSV](https://tcgcsv.com), which mirrors TCGPlayer pricing daily around 20:00 UTC. No API key is required. The Sorcery category ID is `77`.

Sets currently tracked:

| Group ID | Set |
|----------|-----|
| 23335 | Alpha |
| 23336 | Beta |
| 23588 | Arthurian Legends |
| 23778 | Arthurian Legends Promo |
| 23514 | Dust Reward Promos |
| 24378 | Dragonlord |
| 24471 | Gothic |

## Database schema

**cards** — one row per product (foil and non-foil are separate rows). Key fields: `product_id`, `name`, `clean_name`, `image_url`, `rarity`, `cost` (TEXT — handles "X"), `threshold`, `element`, `card_type`, `group_id`, `foil` (INTEGER 0/1).

**prices** — daily price history. Composite primary key `(product_id, sub_type_name, date_fetched)` prevents duplicates and accumulates one row per card per day. Fields: `low_price`, `mid_price`, `high_price`, `market_price`.

**decks** — `deck_id` (AUTOINCREMENT), `name`, `created_at`.

**deck_cards** — junction table. Composite primary key `(deck_id, product_id, zone)` allows the same card to exist in multiple zones within a deck. Valid zones: `maindeck`, `sitedeck`, `collection`, `avatar`, `maybeboard`.

## CLI usage

```bash
# Sync cards and prices manually
python src/main.py sync

# Browse cards with filters
python src/main.py cards --element Water --type Minion

# Price history for a specific card
python src/main.py prices 521503

# Deck management
python src/main.py deck create --name "Water Aggro"
python src/main.py deck show --id 1
python src/main.py deck add --id 1 --card 521503 --zone maindeck
```

## Authorship

This project was built collaboratively between Thomas (the developer) and Claude (Anthropic's AI assistant) as a structured learning exercise. The breakdown below reflects how the work was divided.

**Written by Thomas:**
- `src/fetcher.py` — all three API functions (`get_sorcery_groups`, `get_products`, `get_prices`), including the discovery that TCGCSV was the right data source after the direct TCGPlayer API stopped issuing keys
- `src/database.py` (first version) — full schema design, all table definitions, `save_cards`, `save_prices`, `save_deck`, `add_card_to_deck`, `remove_card_from_deck`, `get_cards` dynamic filter query, `get_prices`
- `src/sync.py` — both sync functions
- `src/models.py` — the `Deck` class with `save`, `load`, `add_card`, `remove_card`, `decrement_card`, `delete`
- `src/main.py` — CLI with argparse subcommands (`sync`, `cards`, `prices`, `deck`)

Key schema decisions made independently by Thomas: storing `cost` as TEXT to handle "X" cost cards, using a composite primary key on `deck_cards` to allow the same card in multiple zones, the `INSERT OR IGNORE` + `ON CONFLICT DO UPDATE` pattern for upserts, and using `sqlite3.Row` for named column access.

Thomas also independently caught a data issue (Gothic set missing `extCardCategory`) by verifying API responses directly — a good example of not taking generated code on trust.

**Written by Claude:**
- `api.py` — FastAPI routes, Pydantic models, lifespan startup sync
- `src/database.py` (later additions) — `get_deck_with_cards` with price joining, `get_all_decks` with avatar image lookup, `get_latest_price`, `decrement_card_in_deck` single-connection fix
- `templates/` — all three HTML templates
- `static/css/` — all CSS
- `static/js/` — all three JavaScript files

**Designed by Thomas, implemented by Claude:**
The frontend was Thomas's vision throughout — layout choices, feature decisions (slide-out panels, grouping modes, zone checkboxes controlling charts, browse cards gallery, price summary), and UX flow were all specified by Thomas. Claude translated those requirements into working code.

## Learning context

This project is Phase 1 of a personal 24-month roadmap from data analyst to AI/ML engineer. The objective was Python fluency through project-driven learning — understanding every line rather than copying solutions.

The approach used was Socratic: Thomas reasoned through problems before seeing solutions, and Claude provided explanations and concept diagrams rather than just answers. The backend (Python, SQLite, API design) was written independently. The frontend (HTML/CSS/JS) was a new domain — Claude built it to Thomas's specifications while explaining the underlying concepts.

Key concepts practised: REST API consumption, SQLite schema design, FastAPI, Jinja2 templating, vanilla JS (fetch, async/await, DOM manipulation, template literals), CSS Grid layout, and project structure.
