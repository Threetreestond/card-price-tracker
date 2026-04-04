import argparse
from database import create_tables, get_cards, get_prices
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

    args = parser.parse_args()

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
    else:
        parser.print_help()

if __name__ == "__main__":
    create_tables()
    main()