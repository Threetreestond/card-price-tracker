import argparse

from config import DB_PATH
from context_manager import get_db_connection
from database import create_tables, get_cards, get_cards_by_ids, get_prices
from models import Deck
from sync import sync_cards, sync_prices


def main():
    """
    Entry point for the Sorcery Card Price Tracker CLI.
    Uses argparse subparsers to route commands to the correct handler.

    Commands:
      sync              — fetch latest cards and prices from TCGCSV
      cards             — browse and filter cards
      prices <id>       — show price history for a card by product_id
      deck <action>     — create, show, or add cards to a deck
    """
    # Main parser — handles the top-level command name
    parser = argparse.ArgumentParser(description="Sorcery Card Price Tracker")
    # subparsers allows different commands (sync, cards, prices, deck)
    # dest="command" stores which command was used in args.command
    subparsers = parser.add_subparsers(dest="command")

    # --- sync command ---
    # No arguments needed — just fetches everything
    subparsers.add_parser("sync", help="Fetch latest cards and prices")

    # --- cards command ---
    # All filters are optional — omitting them returns all cards
    cards_parser = subparsers.add_parser("cards", help="Browse cards")
    cards_parser.add_argument("--element", type=str)
    cards_parser.add_argument("--type", type=str)
    cards_parser.add_argument("--cost", type=str)
    cards_parser.add_argument("--rarity", type=str)
    # store_true means --foil sets args.foil = True, omitting it sets False
    cards_parser.add_argument("--foil", action="store_true")

    # --- prices command ---
    # product_id is positional (no --) so it must always be provided
    prices_parser = subparsers.add_parser("prices", help="Show price history for a card")
    prices_parser.add_argument("product_id", type=int)

    # --- deck command ---
    # action is positional with fixed choices: create, show, add
    # Named optional arguments (--name, --id, --card, --zone) vary by action
    deck_parser = subparsers.add_parser("deck", help="Manage decks")
    deck_parser.add_argument("action", choices=["create", "show", "add"])
    deck_parser.add_argument("--name", type=str, help="Deck name for create")
    deck_parser.add_argument("--id", type=int, help="Deck ID for show/add")
    deck_parser.add_argument("--card", type=int, help="Product ID to add")
    deck_parser.add_argument(
        "--zone", type=str, help="Zone to add card to: maindeck, sitedeck, collection, avatar, maybeboard"
    )

    # Parse the arguments from the command line
    args = parser.parse_args()

    # --- Route to the correct handler ---
    with get_db_connection(DB_PATH) as conn:
        create_tables(conn)
        if args.command == "sync":
            print("Syncing cards...")
            sync_cards(conn)
            print("Syncing prices...")
            sync_prices(conn)
            print("Done")

        elif args.command == "cards":
            # Pass all filter args directly — None values are ignored by get_cards()
            cards = get_cards(
                conn, 
                element=args.element, 
                card_type=args.type, 
                cost=args.cost, 
                rarity=args.rarity, 
                foil=args.foil
                )
            print(f"Found {len(cards)} cards\n")
            # :<40 left-aligns the value in a 40-character wide field for column alignment
            for card in cards:
                print(f"{card['name']:<40} {card['rarity']:<15} Cost: {card['cost']:<5} {card['element']}")

        elif args.command == "prices":
            prices = get_prices(conn, product_id=args.product_id)
            print(f"Found {len(prices)} prices\n")
            for price in prices:
                print(
                    f"Date: {price['date_fetched']}\n"
                    f"Market Price: {price['market_price']}\n"
                    f"Low Price: {price['low_price']}\n"
                    f"High Price: {price['high_price']}\n"
                )

        elif args.command == "deck":
            if args.action == "create":
                # Create a new Deck object and save it to get a deck_id
                deck = Deck(name=args.name)
                deck.save(conn)
                print(f"Created deck '{deck.name}' with ID: '{deck.deck_id}'")

            elif args.action == "show":
                # Load deck by ID — load() populates both name and cards from the database
                deck = Deck(deck_id=args.id)
                deck.load(conn)
                print(f"Deck '{deck.name}' (ID: {deck.deck_id}) — {len(deck.cards)} cards\n")

                # Fetch all card details in one query using the product_ids from the deck.
                # deck.cards.keys() returns (product_id, zone) tuples — we extract just
                # the product_ids for the lookup, then build a {product_id: card} dict.
                card_lookup = {
                    card["product_id"]: card for card in get_cards_by_ids(conn, [pid for pid, zone in deck.cards])
                }
                # Unpack the tuple key into product_id and zone for display
                for (product_id, zone), quantity in deck.cards.items():
                    card = card_lookup[product_id]
                    print(f"{card['name']:<40} {zone:<12} x{quantity}")

            elif args.action == "add":
                # Load existing deck by ID, then add the specified card to the given zone
                deck = Deck(deck_id=args.id)
                deck.load(conn)
                deck.add_card(conn, product_id=args.card, zone=args.zone)

        else:
            # No command provided — show help text
            parser.print_help()


if __name__ == "__main__":
    # Ensure tables exist before any command runs
    main()
