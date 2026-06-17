import re


def normalize_text(text):
    text = str(text).lower().strip()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def safe_number(value):
    try:
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()

        if text == "" or text.lower() in ["nan", "none"]:
            return 0.0

        text = text.replace("TL", "")
        text = text.replace("₺", "")
        text = text.strip()

        # 21.000 TL -> 21000
        if "." in text and "," not in text:
            parts = text.split(".")
            if len(parts[-1]) == 3:
                text = text.replace(".", "")

        # 21.500,75 -> 21500.75
        if "," in text:
            text = text.replace(".", "")
            text = text.replace(",", ".")

        return float(text)

    except Exception:
        return 0.0


def money(value):
    return f"{safe_number(value):,.0f} TL".replace(",", ".")


def extract_first_number(value):
    text = str(value).lower().replace(",", ".")
    found = re.findall(r"\d+\.?\d*", text)

    if not found:
        return 0.0

    return float(found[0])