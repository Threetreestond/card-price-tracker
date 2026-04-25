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

import json
import logging
import re
import sqlite3
import unicodedata
from urllib.parse import quote

import requests

from config import DB_PATH
from context_manager import get_db_connection
from database import add_card_to_deck, save_deck
from models import Deck

log = logging.getLogger(__name__)

# ── Set code → TCGCSV group_id mapping ───────────────────────────────────────
SET_CODE_TO_GROUP_ID = {
    "alp": 23335,  # Alpha
    "bet": 23336,  # Beta
    "pro": 23514,  # Dust Reward / Promotional
    "art": 23588,  # Arthurian Legends
    "alt": 23778,  # Arthurian Legends Promo
    "dra": 24378,  # Dragonlord
    "got": 24471,  # Gothic
}

ZONE_MAP = {
    "avatar": "avatar",
    "sideboard": "collection",
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
    name = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    name = name.replace("!", "").replace("?", "").replace("-", " ").strip()
    return name


# ── Public entry point ────────────────────────────────────────────────────────


def import_curiosa_deck(curiosa_url: str) -> dict:
    deck_id_str = _extract_deck_id(curiosa_url)
    if not deck_id_str:
        raise ValueError(f"Could not extract deck ID from URL: {curiosa_url}")

    log.info("Fetching Curiosa deck: %s", deck_id_str)

    metadata = _fetch_metadata(deck_id_str)
    deck_name = metadata.get("name", "Imported Deck")
    log.info("Deck name: %s", deck_name)

    zones = _fetch_all_zones(deck_id_str)
    total = sum(len(v) for v in zones.values())
    log.info("Retrieved %d total card entries across all zones", total)

    with get_db_connection(DB_PATH) as conn:
        deck = Deck(name=deck_name)
        new_deck_id = save_deck(conn, deck)
        if new_deck_id is None:
            raise RuntimeError("Failed to create deck — no ID returned")
        imported, unmatched = _import_cards(conn, new_deck_id, zones)

    log.info(
        "Import complete — deck_id=%s, imported=%d, unmatched=%d",
        new_deck_id, imported, len(unmatched),
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
    return resp.json()[0]["result"]["data"]["json"] # type: ignore[no-any-return]


def _fetch_all_zones(deck_id: str) -> dict[str, list]:
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
    result: dict[str, list] = {}

    for i, zone_key in enumerate(zone_keys):
        try:
            payload = data[i]["result"]["data"]["json"]
        except (IndexError, KeyError, TypeError) as e:
            log.warning("Zone '%s' fetch failed: %s", zone_key, e)
            result[zone_key] = []
            continue

        if payload is None:
            result[zone_key] = []
        elif isinstance(payload, list):
            result[zone_key] = payload
        elif isinstance(payload, dict):
            result[zone_key] = [payload]
        else:
            result[zone_key] = []

        log.info("  Zone '%s': %d cards", zone_key, len(result[zone_key]))

    return result


# ── Database helpers ──────────────────────────────────────────────────────────


def _import_cards(
    conn: sqlite3.Connection, deck_id: int, zones: dict[str, list]
) -> tuple[int, list[str]]:
    imported = 0
    unmatched: list[str] = []

    for zone_key, entries in zones.items():
        for entry in entries:
            card_data = entry.get("card", {})
            variant_data = entry.get("variant", {})
            quantity = entry.get("quantity", 1)

            card_name = card_data.get("name", "")
            if not card_name:
                continue

            if zone_key == "decklist":
                category = card_data.get("category", "Spell")
                local_zone = "sitedeck" if category == "Site" else "maindeck"
            else:
                local_zone = ZONE_MAP.get(zone_key, zone_key)

            set_card = variant_data.get("setCard", {})
            set_code = set_card.get("set", {}).get("code", "")
            is_foil = variant_data.get("finish", "Standard").lower() == "foil"
            group_id = SET_CODE_TO_GROUP_ID.get(set_code)

            product_id = _find_product_id(conn, card_name, group_id, is_foil)

            if product_id is None:
                log.warning("No match: '%s' (set=%s, foil=%s)", card_name, set_code, is_foil)
                unmatched.append(card_name)
                continue

            add_card_to_deck(conn, deck_id, product_id, local_zone, quantity)
            imported += 1

    return imported, unmatched


def _find_product_id(
    conn: sqlite3.Connection, card_name: str, group_id: int | None, is_foil: bool
) -> int | None:
    foil_suffix = " (Foil)" if is_foil else ""
    exact_name = card_name + foil_suffix
    normalised_name = _normalise_name(card_name) + foil_suffix

    # Attempt 1: exact name, exact set
    if group_id is not None:
        row = conn.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
            (exact_name, group_id),
        ).fetchone()
        if row:
            return row[0]  # type: ignore[no-any-return]

    # Attempt 2: normalised name, exact set
    if group_id is not None and normalised_name != exact_name:
        row = conn.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
            (normalised_name, group_id),
        ).fetchone()
        if row:
            return row[0]  # type: ignore[no-any-return]

    # Attempt 3: normalised name, any set
    row = conn.execute(
        "SELECT product_id FROM cards WHERE clean_name = ? ORDER BY group_id DESC LIMIT 1",
        (normalised_name,),
    ).fetchone()
    if row:
        return row[0]  # type: ignore[no-any-return]

    # Attempt 4: foil fallback to non-foil
    if is_foil:
        base_norm = _normalise_name(card_name)
        if group_id is not None:
            row = conn.execute(
                "SELECT product_id FROM cards WHERE clean_name = ? AND group_id = ?",
                (base_norm, group_id),
            ).fetchone()
            if row:
                return row[0]  # type: ignore[no-any-return]
        row = conn.execute(
            "SELECT product_id FROM cards WHERE clean_name = ? ORDER BY group_id DESC LIMIT 1",
            (base_norm,),
        ).fetchone()
        if row:
            return row[0]  # type: ignore[no-any-return]

    return None