import argparse
from database import create_tables, get_cards, get_prices, get_cards_by_ids
from models import Deck
from sync import sync_cards, sync_prices

def main():
    parser = argparse.ArgumentParser(description="Sorcery Card Price Tracker")
    subparsers = parser.add_subparsers(dest="command")

    # sync command
    subparsers.add_parser("sync", help="Fetch latest cards and prices")

    # cards command
    cards_parser = subparsers.add_parser("cards", help="Browse cards")
    cards_parser.add_argument("--element", type=str)
    cards_parser.add_argument("--type", type=str)
    cards_parser.add_argument("--cost", type=str)
    cards_parser.add_argument("--rarity", type=str)
    cards_parser.add_argument("--foil", action="store_true")

    # prices command
    prices_parser = subparsers.add_parser("prices", help="Show price history for a card")
    prices_parser.add_argument("product_id", type=int)

    # deck commands (create, show, add)
    deck_parser = subparsers.add_parser("deck", help="Manage decks")
    deck_parser.add_argument("action", choices=["create", "show", "add"])
    deck_parser.add_argument("--name", type=str, help="Deck name for create")
    deck_parser.add_argument("--id", type=int, help="Deck ID for show/add")
    deck_parser.add_argument("--card", type=int, help="Product ID to add")
    deck_parser.add_argument("--zone", type=str, help="Card Zone Location to add to")


    # args parser
    args = parser.parse_args()

    # command checker
    if args.command == "sync":
        print("Syncing cards...")
        sync_cards()
        print("Syncing prices...")
        sync_prices()
        print("Done")

    elif args.command == "cards":
        cards = get_cards(element=args.element, card_type=args.type, cost=args.cost, rarity=args.rarity, foil=args.foil)
        print(f"Found {len(cards)} cards\n")
        for card in cards:
            print(f"{card['name']:<40} {card['rarity']:<15} Cost: {card['cost']:<5} {card['element']}")

    elif args.command == "prices":
        prices = get_prices(product_id=args.product_id)
        print(f"Found {len(prices)} prices\n")
        for price in prices:
            print(f"Date: {price['date_fetched']}\nMarket Price: {price['market_price']}\nLow Price: {price['low_price']}\nHigh Price: {price['high_price']}\n")

    elif args.command == "deck":
        if args.action == "create":
            deck = Deck(name=args.name)
            deck.save()
            print(f"Created deck '{deck.name}' with ID: '{deck.deck_id}'")
        elif args.action == "show":
            deck = Deck(deck_id=args.id)
            deck.load()
            print(f"Deck '{deck.name} with ID: '{deck.deck_id}' contains the following '{len(deck.cards)}' cards")
            card_lookup = {card['product_id']: card for card in get_cards_by_ids(
                [pid for pid, zone in deck.cards.keys()]
            )}
            for (product_id, zone), quantity in deck.cards.items():
                card = card_lookup[product_id]
                print(f"{card['name']:<40} {zone:<12} x{quantity}")

        elif args.action == "add":
            deck = Deck(deck_id=args.id)
            deck.load()
            deck.add_card(product_id=args.card, zone=args.zone)

    else:
        parser.print_help()

if __name__ == "__main__":
    create_tables()
    main()