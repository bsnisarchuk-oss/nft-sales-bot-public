# Извлечение адресов из trace: поиск всех адресоподобных строк в sample_trace.json
import re
from pathlib import Path

# Friendly TON-адреса: EQ/UQ + 46 символов
RE_FRIENDLY = re.compile(r"(?:EQ|UQ)[A-Za-z0-9_-]{46}")

# Raw TON-адреса: 0: + 64 hex символа
RE_RAW = re.compile(r"0:[0-9a-fA-F]{64}")


def main():
    trace_path = Path("data/sample_trace.json")
    if not trace_path.exists():
        raise FileNotFoundError("data/sample_trace.json not found. Run: py -m tools.dump_trace")

    # Читаем как текст, чтобы найти все вхождения через regex
    text = trace_path.read_text(encoding="utf-8")

    friendly = sorted(set(RE_FRIENDLY.findall(text)))
    raw = sorted(set(RE_RAW.findall(text)))

    print("Friendly addresses found:", len(friendly))
    for addr in friendly[:30]:
        print(" ", addr)

    print("\nRaw addresses found:", len(raw))
    for addr in raw[:30]:
        print(" ", addr)


if __name__ == "__main__":
    main()
