# Тест парсера событий NFT: проверка работы парсера на sample_events.json
import json
from pathlib import Path

from tools.legacy_parser import parse_sales_from_events


def main():
    # Путь относительно корня проекта
    events_path = Path(__file__).resolve().parent.parent / "data" / "sample_events.json"

    if not events_path.exists():
        print(f"Файл {events_path} не найден!")
        print("Сначала запусти: py tools/dump_events.py")
        return

    with open(events_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # пока можешь поставить пустой set, чтобы увидеть все покупки
    sales = parse_sales_from_events(payload, tracked_collections=set())

    print("Sales events:", len(sales))
    for s in sales[:3]:
        print("Event:", s.event_id, "items:", len(s.items), "total:", s.total_price_ton)
        for it in s.items:
            print("-", it.collection_name, "|", it.nft_name, "|", it.price_ton, "TON")


if __name__ == "__main__":
    main()
