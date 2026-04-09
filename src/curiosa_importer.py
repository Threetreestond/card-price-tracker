"""
curiosa_importer.py
Imports a public Curiosa deck into the local database by calling
Curiosa's internal tRPC API — the same endpoints the browser uses.

WARNING: This relies on undocumented internal endpoints. It may break
if Curiosa changes their API. Accepted risk for a community tool.

Confirmed procedure names (from DevTools network capture):
    deck.getDecklistById  → spellbook + sites mixed (array)
    deck.getAvatarById    → avatar card (single object)
    deck.getSideboardById → sideboard cards (array)
    deck.getMaybeboardById→ maybeboard cards (array)

All four are batched in a single GET request with input {"id": "...", "tracking": false}.
The decklist zone contains both Spells and Sites — we split them by card.category.

Usage:
    from curiosa_importer import import_curiosa_deck
    result = import_curiosa_deck("https://curiosa.io/decks/cmlumsqg400ua04l8i2e71kih")
"""

import re
import json
import logging
import unicodedata
import requests
from urllib.parse import quote
import sqlite3

log = logging.getLogger(__name__)

# ── Set code → TCGCSV group_id mapping ───────────────────────────────────────
SET_CODE_TO_GROUP_ID = {
    "alp": 23335,   # Alpha
    "bet": 23336,   # Beta
    "pro": 23514,   # Dust Reward / Promotional
    "art": 23588,   # Arthurian Legends
    "alt": 23778,   # Arthurian Legends Promo
    "dra": 24378,   # Dragonlord
    "got": 24471,   # Gothic
}

# Non-decklist zones map directly to local zone names
ZONE_MAP = {
    "avatar":     "avatar",
    "sideboard":  "sideboard",
    "maybeboard": "maybeboard",
}

CURIOSA_BASE = "https://curiosa.io/api/trpc"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://curiosa.io",
}


# ── Name normalisation ────────────────────────────────────────────────────────

def _normalise_name(name: str) -> str:
    """
    Normalises a card name for DB matching.
    Handles two known mismatches between Curiosa and TCGCSV:
      - Accented characters: Stefánia → Stefania
      - Punctuation TCGPlayer omits: Guards! → Guards, Zap! → Zap
    Only used at match time — stored names are never altered.
    """
    name = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    name = name.replace('!', '').replace('?', '').strip()
    return name


# ── Public entry point ────────────────────────────────────────────────────────

def import_curiosa_deck(curiosa_url: str, db_path: str = "data/cards.db") -> dict:
    """
    Fetches a public Curiosa deck and imports it into the local database.

    Returns:
        {
          "deck_id": int,
          "deck_name": str,
          "imported": int,
          "unmatched": list[str]
        }
    """
    deck_id_str = _extract_deck_id(curiosa_url)
    if not deck_id_str:
        raise ValueError(f"Could not extract deck ID from URL: {curiosa_url}")

    log.info(f"Fetching Curiosa deck: {deck_id_str}")

    metadata = _fetch_metadata(deck_id_str)
    deck_name = metadata.get("name", "Imported Deck")
    log.info(f"Deck name: {deck_name}")

    zones = _fetch_all_zones(deck_id_str)
    total = sum(len(v) for v in zones.values())
    log.info(f"Retrieved {total} total card entries across all zones")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        new_deck_id = _create_deck(conn, deck_name)
        imported, unmatched = _import_cards(conn, new_deck_id, zones)
        conn.commit()
    finally:
        conn.close()

    log.info(
        f"Import complete — deck_id={new_deck_id}, "
        f"imported={imported}, unmatched={len(unmatched)}"
    )
    return {
        "deck_id": new_deck_id,
        "deck_name": deck_name,
        "imported": imported,
        "unmatched": unmatched,
    }


# ── URL / tRPC helpers ────────────────────────────────────────────────────────

def _extract_deck_id(url: str) -> str | None:
    match = re.search(r"curiosa\.io/decks/([a-z0-9]+)", url)
    return match.group(1) if match else None


def _fetch_metadata(deck_id: str) -> dict:
    batch_input = json.dumps({"0": {"json": {"id": deck_id}}})
    url = f"{CURIOSA_BASE}/deck.getById?batch=1&input={quote(batch_input)}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()[0]["result"]["data"]["json"]


def _fetch_all_zones(deck_id: str) -> dict[str, list]:
    """
    Single batch GET for all four zones — mirrors exactly what the browser does.
    """
    procedures = [
        "deck.getDecklistById",
        "deck.getAvatarById",
        "deck.getSideboardById",
        "deck.getMaybeboardById",
    ]
    entry = {"json": {"id": deck_id, "tracking": False}}
    batch_input = json.dumps({str(i): entry for i in range(4)})
    url = f"{CURIOSA_BASE}/{','.join(procedures)}?batch=1&input={quote(batch_input)}"

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    zone_keys = ["decklist", "avatar", "sideboard", "maybeboard"]
    result = {}

    for i, zone_key in enumerate(zone_keys):
        try:
            payload = data[i]["result"]["data"]["json"]
        except (IndexError, KeyError, TypeError) as e:
            log.warning(f"Zone '{zone_key}' fetch failed: {e}")
            result[zone_key] = []
            continue

        if payload is None:
            result[zone_key] = []
        elif isinstance(payload, list):
            result[zone_key] = payload
        elif isinstance(payload, dict):
            result[zone_key] = [payload]  # avatar is a single object
        else:
            result[zone_key] = []

        log.info(f"  Zone '{zone_key}': {len(result[zone_key])} cards")

    return result


# ── Database helpers ──────────────────────────────────────────────────────────

def _create_deck(conn: sqlite3.Connection, name: str) -> int:
    from datetime import date
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO decks (name, created_at) VALUES (?, ?)",
        (name, str(date.today()))
    )
    return cursor.lastrowid


def _import_cards(
    conn: sqlite3.Connection,
    deck_id: int,
    zones: dict[str, list]
) -> tuple[int, list]:
    cursor = conn.cursor()
    imported = 0
    unmatched = []

    for zone_key, entries in zones.items():
        for entry in entries:
            card_data = entry.get("card", {})
            variant_data = entry.get("variant", {})
            quantity = entry.get("quantity", 1)

            card_name = card_data.get("name", "")
            if not card_name:
                continue

            # The "decklist" zone contains both Spells and Sites mixed together.
            # Split by card.category so sites land in sitedeck, not maindeck.
            if zone_key == "decklist":
                category = card_data.get("category", "Spell")
                local_zone = "sitedeck" if category == "Site" else "maindeck"
            else:
                local_zone = ZONE_MAP.get(zone_key, zone_key)

            set_card = variant_data.get("setCard", {})
            set_code = set_card.get("set", {}).get("code", "")
            is_foil = variant_data.get("finish", "Standard").lower() == "foil"
            group_id = SET_CODE_TO_GROUP_ID.get(set_code)

            product_id = _find_product_id(cursor, card_name, group_id, is_foil)

            if product_id is None:
                log.warning(f"No match: '{card_name}' (set={set_code}, foil={is_foil})")
                unmatched.append(card_name)
                continue

            cursor.execute("""
                INSERT INTO deck_cards (deck_id, product_id, zone, quantity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (deck_id, product_id, zone)
                DO UPDATE SET quantity = quantity + ?
            """, (deck_id, product_id, local_zone, quantity, quantity))
            imported += 1

    return imported, unmatched


def _find_product_id(
    cursor: sqlite3.Cursor,
    card_name: str,
    group_id: int | None,
    is_foil: bool
) -> int | None:
    """
    Tiered lookup with name normalisation to handle:
      - Punctuation differences (Guards! vs Guards)
      - Accent differences (Stefánia vs Stefania)

    Attempts in order:
      1. Exact name + set + foil
      2. Normalised name + set + foil
      3. Normalised name, any set
      4. If foil requested but not found, retry without foil
    """
    foil_suffix = " (Foil)" if is_foil else ""
    exact_name = card_name + foil_suffix
    normalised_name = _normalise_name(card_name) + foil_suffix

    # Attempt 1: exact name, exact set
    if group_id is not None:
        cursor.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
            (exact_name, group_id)
        )
        row = cursor.fetchone()
        if row:
            return row[0]

    # Attempt 2: normalised name, exact set
    if group_id is not None and normalised_name != exact_name:
        cursor.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
            (normalised_name, group_id)
        )
        row = cursor.fetchone()
        if row:
            return row[0]

    # Attempt 3: normalised name, any set
    cursor.execute(
        "SELECT product_id FROM cards WHERE clean_name = ? ORDER BY group_id DESC LIMIT 1",
        (normalised_name,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    # Attempt 4: foil fallback to non-foil
    if is_foil:
        base_norm = _normalise_name(card_name)
        if group_id is not None:
            cursor.execute(
                "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
                (base_norm, group_id)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        cursor.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? ORDER BY group_id DESC LIMIT 1",
            (base_norm,)
        )
        row = cursor.fetchone()
        if row:
            return row[0]

    return None
