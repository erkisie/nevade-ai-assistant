import os
import re
import json
import mimetypes
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# =====================================================
# VISION ENGINE
# Amaç:
# 1) Gemini Vision ile yüklenen görselden ürün tipini çıkarır.
# 2) Eğer Gemini çalışmazsa açıklama + dosya adı + manuel seçim fallback olur.
# 3) Katalogda görsel/anlam bazlı ürün eşleştirir.
# =====================================================


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))


def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }

    for tr_char, simple_char in replacements.items():
        text = text.replace(tr_char, simple_char)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def safe_number(value):
    try:
        if pd.isna(value):
            return 0

        if isinstance(value, str):
            value = (
                value.replace("TL", "")
                .replace("₺", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )

        return float(value)

    except Exception:
        return 0


def detect_visual_product_type(description="", filename=""):
    text = normalize_text(f"{description} {filename}")

    detected = []

    if any(x in text for x in ["buzdolabi", "buz dolabi", "no frost", "sogutucu", "minibar", "mini bar", "fridge", "refrigerator"]):
        detected.append("buzdolabi")

    if any(x in text for x in ["camasir", "camasir makinesi", "washing machine"]):
        detected.append("camasir_makinesi")

    if any(x in text for x in ["bulasik", "bulasik makinesi", "dishwasher"]):
        detected.append("bulasik_makinesi")

    if any(x in text for x in ["tv", "televizyon", "smart tv", "akilli tv", "ekran", "television"]):
        detected.append("televizyon")

    if any(x in text for x in ["supurge", "robot supurge", "dikey supurge", "temizlik", "vacuum"]):
        detected.append("supurge")

    if any(x in text for x in ["laptop", "notebook", "bilgisayar", "computer"]):
        detected.append("laptop")

    if any(x in text for x in ["telefon", "iphone", "galaxy", "android", "phone", "smartphone"]):
        detected.append("telefon")

    if any(x in text for x in ["klima", "air conditioner"]):
        detected.append("klima")

    if any(x in text for x in ["firin", "ankastre", "ocak", "oven"]):
        detected.append("firin")

    return list(dict.fromkeys(detected))


def product_type_to_keywords(product_type):
    mapping = {
        "buzdolabi": ["buzdolabi", "no frost", "sogutucu", "minibar", "mini bar"],
        "camasir_makinesi": ["camasir"],
        "bulasik_makinesi": ["bulasik"],
        "televizyon": ["televizyon", "smart tv", "tv"],
        "supurge": ["supurge", "temizlik"],
        "laptop": ["laptop", "notebook", "bilgisayar"],
        "telefon": ["telefon", "iphone", "galaxy", "android"],
        "klima": ["klima"],
        "firin": ["firin", "ankastre", "ocak"],
    }

    return mapping.get(product_type, [])


def row_to_text(row):
    return normalize_text(
        f"{row.get('product_name', '')} "
        f"{row.get('category', '')} "
        f"{row.get('brand', '')} "
        f"{row.get('description', '')} "
        f"{row.get('features', '')} "
        f"{row.get('use_case', '')} "
        f"{row.get('payment_options', '')}"
    )


# =====================================================
# GEMINI VISION
# =====================================================

def parse_json_safely(text):
    if not text:
        return None

    raw = str(text).strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None


def analyze_image_with_gemini(image_bytes, filename=""):
    """
    Görseli Gemini ile analiz eder.
    Dönen yapı:
    {
        "success": True/False,
        "product_type": "...",
        "detected_types": [...],
        "description": "...",
        "keywords": [...],
        "confidence": 0-100,
        "raw_text": "..."
    }
    """

    if not GEMINI_API_KEY:
        return {
            "success": False,
            "reason": "GEMINI_API_KEY bulunamadı.",
            "product_type": None,
            "detected_types": [],
            "description": "",
            "keywords": [],
            "confidence": 0,
            "raw_text": "",
        }

    if not image_bytes:
        return {
            "success": False,
            "reason": "Görsel verisi boş.",
            "product_type": None,
            "detected_types": [],
            "description": "",
            "keywords": [],
            "confidence": 0,
            "raw_text": "",
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        mime_type = mimetypes.guess_type(filename or "")[0] or "image/jpeg"

        prompt = """
Bu görseldeki ürünü Nevade e-ticaret kataloğu için analiz et.

Sadece JSON döndür. Açıklama yazma.

Geçerli product_type değerleri:
- buzdolabi
- camasir_makinesi
- bulasik_makinesi
- televizyon
- supurge
- laptop
- telefon
- klima
- firin
- unknown

JSON formatı:
{
  "product_type": "buzdolabi",
  "detected_types": ["buzdolabi"],
  "description": "Görselde beyaz renkli bir buzdolabı görünüyor.",
  "keywords": ["buzdolabi", "no frost", "beyaz esya"],
  "confidence": 85
}

Kurallar:
- Emin değilsen product_type: "unknown" yap.
- Marka/fiyat/stok uydurma.
- Sadece görselde görünen ürün tipini tahmin et.
- Türkçe description yaz.
"""

        response = client.models.generate_content(
            model=GEMINI_VISION_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.05,
                max_output_tokens=500,
            ),
        )

        raw_text = getattr(response, "text", "") or ""
        parsed = parse_json_safely(raw_text)

        if not parsed:
            return {
                "success": False,
                "reason": "Gemini JSON parse edilemedi.",
                "product_type": None,
                "detected_types": [],
                "description": "",
                "keywords": [],
                "confidence": 0,
                "raw_text": raw_text,
            }

        product_type = parsed.get("product_type") or "unknown"

        detected_types = parsed.get("detected_types") or []

        if product_type and product_type != "unknown" and product_type not in detected_types:
            detected_types.append(product_type)

        return {
            "success": True,
            "reason": "Gemini Vision görsel analizi yaptı.",
            "product_type": product_type,
            "detected_types": detected_types,
            "description": parsed.get("description", ""),
            "keywords": parsed.get("keywords", []),
            "confidence": parsed.get("confidence", 0),
            "raw_text": raw_text,
        }

    except Exception as e:
        return {
            "success": False,
            "reason": f"Gemini Vision hata: {e}",
            "product_type": None,
            "detected_types": [],
            "description": "",
            "keywords": [],
            "confidence": 0,
            "raw_text": "",
        }


# =====================================================
# KATALOG EŞLEŞTİRME
# =====================================================

def visual_search_products(products_df, description="", filename="", top_k=8, detected_types=None):
    """
    Görsel açıklaması + dosya adı + Gemini product_type sonucuna göre katalogdan aday ürün döndürür.
    """

    if products_df is None or products_df.empty:
        return pd.DataFrame(), {
            "active": True,
            "reason": "Ürün kataloğu boş.",
            "detected_types": [],
            "filename": filename,
            "description": description,
        }

    detected_types = detected_types or detect_visual_product_type(description, filename)

    df = products_df.copy()

    query_text = normalize_text(f"{description} {filename}")
    query_tokens = [x for x in query_text.split() if len(x) > 2]

    def score_row(row):
        text = row_to_text(row)
        score = 0

        for token in query_tokens:
            if token in text:
                score += 5

        for product_type in detected_types:
            keywords = product_type_to_keywords(product_type)

            if any(keyword in text for keyword in keywords):
                score += 80
            else:
                score -= 35

        if normalize_text(row.get("stock_status", "")) == "stokta":
            score += 8

        if safe_number(row.get("price", 0)) > 0:
            score += 2

        return score

    df["vision_score"] = df.apply(score_row, axis=1)

    if detected_types:
        df = df[df["vision_score"] > 0]

    df = df.sort_values("vision_score", ascending=False).head(top_k)

    info = {
        "active": True,
        "reason": "Görsel açıklaması / Gemini Vision / dosya adına göre ürün eşleştirmesi yapıldı.",
        "detected_types": detected_types,
        "filename": filename,
        "description": description,
        "result_count": len(df),
    }

    return df, info


def vision_query_text(description="", filename="", detected_types=None, gemini_description="", keywords=None):
    detected_types = detected_types or detect_visual_product_type(description, filename)
    keywords = keywords or []

    parts = []

    if detected_types:
        parts.extend(detected_types)

    if keywords:
        parts.extend(keywords)

    if gemini_description:
        parts.append(gemini_description)

    if description:
        parts.append(description)

    if filename:
        parts.append(filename)

    return normalize_text(" ".join(parts))


def build_visual_query_from_image(image_bytes=None, filename="", manual_description="", manual_type_text=""):
    """
    App tarafında tek çağrı için kullanılır.
    """

    gemini_result = {
        "success": False,
        "reason": "Görsel analizi çağrılmadı.",
        "product_type": None,
        "detected_types": [],
        "description": "",
        "keywords": [],
        "confidence": 0,
        "raw_text": "",
    }

    if image_bytes:
        gemini_result = analyze_image_with_gemini(image_bytes, filename=filename)

    manual_detected = detect_visual_product_type(manual_type_text, filename)
    description_detected = detect_visual_product_type(manual_description, filename)

    detected_types = []

    if gemini_result.get("detected_types"):
        detected_types.extend(gemini_result.get("detected_types"))

    detected_types.extend(manual_detected)
    detected_types.extend(description_detected)

    detected_types = [x for x in detected_types if x and x != "unknown"]
    detected_types = list(dict.fromkeys(detected_types))

    combined_description = " ".join(
        [
            manual_type_text or "",
            manual_description or "",
            gemini_result.get("description", "") or "",
            " ".join(gemini_result.get("keywords", []) or []),
            filename or "",
        ]
    ).strip()

    generated_query = vision_query_text(
        description=manual_description,
        filename=filename,
        detected_types=detected_types,
        gemini_description=gemini_result.get("description", ""),
        keywords=gemini_result.get("keywords", []),
    )

    return {
        "generated_query": generated_query,
        "combined_description": combined_description,
        "detected_types": detected_types,
        "gemini_result": gemini_result,
    }


if __name__ == "__main__":
    test_products = pd.DataFrame(
        [
            {
                "product_name": "Vestel Mini Bar Buzdolabı 90 L",
                "category": "Beyaz Eşya",
                "brand": "Vestel",
                "description": "Mini buzdolabı ve içecek soğutucu",
                "features": "Kompakt tasarım",
                "use_case": "Balkon, ofis, küçük oda",
                "stock_status": "Stokta",
                "price": 7999,
            },
            {
                "product_name": "Samsung Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "description": "Smart TV",
                "features": "4K ekran",
                "use_case": "Salon",
                "stock_status": "Stokta",
                "price": 12900,
            },
        ]
    )

    result, info = visual_search_products(
        test_products,
        description="buzdolabi sogutucu",
        filename="image.jpg",
        detected_types=["buzdolabi"],
    )

    print(info)
    print(result[["product_name", "vision_score"]])