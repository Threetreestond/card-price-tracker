import pytest
from context_manager import get_db_connection
from database import create_tables, save_deck, get_deck, decrement_card_in_deck, get_cards, delete_deck, add_card_to_deck, save_cards, save_prices, get_all_decks, get_deck_cards, get_prices, get_latest_price
from models import Deck



TEST_CARDS = [
    {
        "productId": 521503,
        "groupId": 100,
        "categoryId": 62,
        "name": "Accursed Albatross",
        "cleanName": "Accursed Albatross",
        "imageUrl": "https://example.com/albatross.jpg",
        "url": "https://example.com/albatross",
        "extendedData": [
            {"name": "Rarity", "value": "Ordinary"},
            {"name": "Description", "value": "A cursed seabird."},
            {"name": "Cost", "value": "1"},
            {"name": "Threshold", "value": "1"},
            {"name": "Element", "value": "Water"},
            {"name": "Type Line", "value": "Minion - Bird"},
            {"name": "CardCategory", "value": "Minion"},
            {"name": "CardType", "value": "Minion"},
            {"name": "Card Subtype", "value": "Bird"},
            {"name": "Power Rating", "value": "2"},
            {"name": "Defense Power", "value": "1"},
            {"name": "Life", "value": ""},
            {"name": "Flavor Text", "value": "It brings only misfortune."},
        ],
    },
    {
        "productId": 521514,
        "groupId": 100,
        "categoryId": 62,
        "name": "Adept Illusionist",
        "cleanName": "Adept Illusionist",
        "imageUrl": "https://example.com/illusionist.jpg",
        "url": "https://example.com/illusionist",
        "extendedData": [
            {"name": "Rarity", "value": "Elite"},
            {"name": "Description", "value": "A master of deception."},
            {"name": "Cost", "value": "3"},
            {"name": "Threshold", "value": "2"},
            {"name": "Element", "value": "Air"},
            {"name": "Type Line", "value": "Minion - Human Mage"},
            {"name": "CardCategory", "value": "Minion"},
            {"name": "CardType", "value": "Minion"},
            {"name": "Card Subtype", "value": "Human Mage"},
            {"name": "Power Rating", "value": "3"},
            {"name": "Defense Power", "value": "3"},
            {"name": "Life", "value": ""},
            {"name": "Flavor Text", "value": "Now you see me."},
        ],
    },
    {
        "productId": 521530,
        "groupId": 100,
        "categoryId": 62,
        "name": "Volcanic Dragon",
        "cleanName": "Volcanic Dragon",
        "imageUrl": "https://example.com/dragon.jpg",
        "url": "https://example.com/dragon",
        "extendedData": [
            {"name": "Rarity", "value": "Exceptional"},
            {"name": "Description", "value": "A beast of molten fury."},
            {"name": "Cost", "value": "5"},
            {"name": "Threshold", "value": "3"},
            {"name": "Element", "value": "Fire"},
            {"name": "Type Line", "value": "Minion - Dragon"},
            {"name": "CardCategory", "value": "Minion"},
            {"name": "CardType", "value": "Minion"},
            {"name": "Card Subtype", "value": "Dragon"},
            {"name": "Power Rating", "value": "6"},
            {"name": "Defense Power", "value": "5"},
            {"name": "Life", "value": ""},
            {"name": "Flavor Text", "value": "The mountain wakes."},
        ],
    },
    {
        "productId": 521540,
        "groupId": 100,
        "categoryId": 62,
        "name": "Accursed Albatross (Foil)",
        "cleanName": "Accursed Albatross",
        "imageUrl": "https://example.com/albatross_foil.jpg",
        "url": "https://example.com/albatross_foil",
        "extendedData": [
            {"name": "Rarity", "value": "Ordinary"},
            {"name": "Description", "value": "A cursed seabird."},
            {"name": "Cost", "value": "1"},
            {"name": "Threshold", "value": "1"},
            {"name": "Element", "value": "Water"},
            {"name": "Type Line", "value": "Minion - Bird"},
            {"name": "CardCategory", "value": "Minion"},
            {"name": "CardType", "value": "Minion"},
            {"name": "Card Subtype", "value": "Bird"},
            {"name": "Power Rating", "value": "2"},
            {"name": "Defense Power", "value": "1"},
            {"name": "Life", "value": ""},
            {"name": "Flavor Text", "value": "It brings only misfortune."},
        ],
    },
]

TEST_PRICES = [
    {"productId": 521503, "subTypeName": "Normal", "lowPrice": 0.05, "midPrice": 0.10, "highPrice": 0.25, "marketPrice": 0.08},
    {"productId": 521503, "subTypeName": "Foil", "lowPrice": 0.50, "midPrice": 1.00, "highPrice": 2.00, "marketPrice": 0.75},
    {"productId": 521514, "subTypeName": "Normal", "lowPrice": 1.50, "midPrice": 2.50, "highPrice": 4.00, "marketPrice": 2.00},
    {"productId": 521530, "subTypeName": "Normal", "lowPrice": 5.00, "midPrice": 8.00, "highPrice": 12.00, "marketPrice": 7.50},
]


@pytest.fixture
def db_conn():
    with get_db_connection(":memory:") as conn:
        create_tables(conn)
        yield conn

@pytest.fixture
def db_with_cards(db_conn):
    for card in TEST_CARDS:
        save_cards(db_conn, card)
    for price in TEST_PRICES:
        save_prices(db_conn, price)

    deck = Deck(name="Test Deck")
    deck.deck_id = save_deck(db_conn, deck)
    add_card_to_deck(db_conn, deck.deck_id, 521503, "maindeck", quantity=3)
    add_card_to_deck(db_conn, deck.deck_id, 521514, "maindeck", quantity=1)
    add_card_to_deck(db_conn, deck.deck_id, 521530, "avatar", quantity=1)

    deck2 = Deck(name="Test Deck 2")
    deck2.deck_id = save_deck(db_conn, deck2)
    add_card_to_deck(db_conn, deck2.deck_id, 521503, "maindeck", quantity=3)
    add_card_to_deck(db_conn, deck2.deck_id, 521514, "maindeck", quantity=1)
    add_card_to_deck(db_conn, deck2.deck_id, 521530, "avatar", quantity=1)
    return db_conn



def test_save_deck(db_conn):
    deck = Deck(name="Test Name")
    deck.deck_id = save_deck(db_conn, deck)
    result = get_deck(db_conn, deck.deck_id) 
    assert result is not None, "a deck should have been saved"
    assert result["name"] == deck.name, "Deck name should match what was saved"


@pytest.mark.parametrize("deck_name", [
    "Water Control",
    "Tom's Deck",
    "Deck with 'quotes' and \"doubles\"",
    "🔥 Fire Deck 🔥",
    "'; DROP TABLE decks; --"
])
def test_save_deck_preserves_name(db_conn, deck_name):
    # same body as your existing test, but using deck_name
    deck = Deck(name=deck_name)
    deck.deck_id = save_deck(db_conn, deck)
    result = get_deck(db_conn, deck.deck_id)
    assert result is not None, "a deck should have been retrieved"
    assert result["name"] == deck.name, "Deck name should match what was saved"


def test_save_deck_empty_name(db_conn):
    deck = Deck(name="")
    deck.deck_id = save_deck(db_conn, deck)
    result = get_deck(db_conn, deck.deck_id)
    assert result is not None, "a deck should have been retrieved"
    assert result["name"] == deck.name, "Deck name should match what was saved"



def test_save_deck_duplicate_name(db_conn):
    deck_one = Deck(name="Duplicate Name")
    deck_one.deck_id = save_deck(db_conn, deck_one)
    result_one = get_deck(db_conn, deck_one.deck_id) 
    
    deck_two = Deck(name="Duplicate Name")
    deck_two.deck_id = save_deck(db_conn, deck_two)
    result_two = get_deck(db_conn, deck_two.deck_id)
    assert result_one is not None and result_two is not None, "both decks should be retrieved succesfully"
    assert result_one["deck_id"] != result_two["deck_id"], "Deck ids should be different"

def test_decrement_card_in_deck_quantity_remains(db_with_cards):
    all_decks = get_all_decks(db_with_cards)
    deck_id = all_decks[0]["deck_id"]
    return_value = decrement_card_in_deck(db_with_cards, deck_id, 521503, "maindeck")
    assert return_value == 0, "this has deleted a qty > 1 card when decrementing by 1 when it should return 0: no row deletion"
    test_card = [card for card in get_deck_cards(db_with_cards, deck_id) if card["product_id"] == 521503 and card["zone"] == "maindeck"]
    assert test_card[0]["quantity"] == 2, "incorrect quantity, expecting 2"
    
def test_decrement_card_in_deck_card_removed(db_with_cards):
    all_decks = get_all_decks(db_with_cards)
    deck_id = all_decks[0]["deck_id"]
    return_value = decrement_card_in_deck(db_with_cards, deck_id, 521514, "maindeck")
    assert return_value == 1, "this has not deleted a qty = 1 card when decrementing by 1 when it should return 1: row deletion"
    test_card = [card for card in get_deck_cards(db_with_cards, deck_id) if card["product_id"] == 521514 and card["zone"] == "maindeck"]
    assert not test_card, "test card should be empty"


def test_delete_deck_with_cards(db_with_cards):
    all_decks = get_all_decks(db_with_cards)
    deck_id = all_decks[0]["deck_id"]
    delete_deck(db_with_cards, deck_id)
    return_value_deck = get_deck(db_with_cards, deck_id)
    return_value_cards = get_deck_cards(db_with_cards, deck_id)
    assert not return_value_deck, "deck_id should not exist anymore after delete_deck is called"
    assert not return_value_cards, "Cards should be deleted for the deck_id that was deleted"

def test_delete_deck_non_existent(db_with_cards):
    return_value = delete_deck(db_with_cards, 999)
    assert return_value == 0, "no rows should be returned as no deck existed to have rows deleted from"


def test_delete_deck_other_deck_untouched(db_with_cards):
    all_decks = get_all_decks(db_with_cards)
    deck_one_id = all_decks[0]["deck_id"]
    deck_two_id = all_decks[1]["deck_id"]
    deck_two_cards = get_deck_cards(db_with_cards, deck_two_id)
    delete_deck(db_with_cards, deck_one_id)
    assert deck_two_cards == get_deck_cards(db_with_cards, deck_two_id), "content should be untouched and they should be equal as deck one was deleted not deck two"



def test_get_cards_no_filters(db_with_cards):
    cards = get_cards(db_with_cards)
    assert len(cards) == 4, "there are 4 cards in the database, all should return with no filters"
    result_ids = {card["product_id"] for card in cards}
    assert result_ids == {521503, 521514, 521530, 521540}, "returned card ids should match test data"

@pytest.mark.parametrize("filters, expected_ids", [
    ({"element": "Water"}, {521503, 521540}),
    ({"rarity": "Ordinary"}, {521503, 521540}),
    ({"cost": "5"}, {521530}),
    ({"element": "Fire"}, {521530}),
    ({"group_id": 100}, {521503, 521514, 521530, 521540}),
    ({"power_rating": 3}, {521514}),
    ({"foil": True}, {521540}),
    ({"foil": False}, {521503, 521514, 521530}),
    ({"element": "Earth"}, set()),
])
def test_get_cards_single_filter(db_with_cards, filters, expected_ids):
    results = get_cards(db_with_cards, **filters)
    result_ids = {card["product_id"] for card in results}
    assert result_ids == expected_ids


@pytest.mark.parametrize("filters, expected_ids", [
    ({"element": "Water", "rarity": "Ordinary"}, {521503, 521540}),
    ({"rarity": "Exceptional", "cost": "5"}, {521530}),
    ({"cost": "5", "element": "Fire"}, {521530}),
    ({"defense_power": 5, "card_type": "Minion"}, {521530}),
])
def test_get_cards_multiple_filters(db_with_cards, filters, expected_ids):
    results = get_cards(db_with_cards, **filters)
    result_ids = {card["product_id"] for card in results}
    assert result_ids == expected_ids



def test_get_prices_no_filter(db_with_cards):
    prices = get_prices(db_with_cards)
    assert len(prices) == 4, "there are 4 cards with prices in the database, all should return with no filters"
    result_ids = {prices[0]["product_id"] for price in prices}
    assert result_ids == {521503, 521514, 521530, 521540}, "returned card ids should match test data"