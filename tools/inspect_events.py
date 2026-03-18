# Инспектор событий: анализ структуры событий из sample_events.json для отладки парсера
import json
from collections import Counter
from pathlib import Path


def main():
    events_path = Path(__file__).resolve().parent.parent / "data" / "sample_events.json"

    if not events_path.exists():
        print("No data/sample_events.json")
        return

    with open(events_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Извлекаем events (поддерживаем разные форматы ответа)
    if isinstance(payload, list):
        events = payload
    elif isinstance(payload, dict):
        events = payload.get("events") or payload.get("data") or payload.get("result") or []
    else:
        events = []

    type_counter = Counter()
    interesting = []

    for ev in events:
        actions = ev.get("actions") or ev.get("event_actions") or []
        if not isinstance(actions, list):
            continue

        for act in actions:
            if not isinstance(act, dict):
                continue

            t = (act.get("type") or act.get("action") or "").lower()
            if t:
                type_counter[t] += 1

            # Ищем интересные действия (purchase/sale/buy)
            dump = json.dumps(act, ensure_ascii=False).lower()
            if any(kw in dump for kw in ("purchase", "sale", "buy")):
                interesting.append(act)

    print("Events:", len(events))
    print("\nTop action types:")
    for t, count in type_counter.most_common(30):
        print(f"  {count:4d} | {t}")

    print("\nInteresting actions (purchase/sale/buy) found:", len(interesting))
    if interesting:
        print("\nFirst sample:")
        print(json.dumps(interesting[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
