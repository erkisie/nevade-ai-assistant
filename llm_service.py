import os
import re
import json
import requests
from dotenv import load_dotenv


# =====================================================
# ENV YÜKLEME
# =====================================================

load_dotenv()


# =====================================================
# TEMEL AYARLAR
# =====================================================

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
LLM_DEBUG = os.getenv("LLM_DEBUG", "false").lower() == "true"


# =====================================================
# GENEL YARDIMCI FONKSİYONLAR
# =====================================================

def debug_print(*args):
    if LLM_DEBUG:
        print(*args)


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


def clean_value(value):
    if value is None:
        return ""

    try:
        if str(value).lower() == "nan":
            return ""
    except Exception:
        pass

    return str(value).strip()


def format_price(value):
    """
    Eğer değer sayı ise 18.500 TL formatına çevirir.
    Eğer zaten string ise temizleyip döndürür.
    """

    if value is None or value == "":
        return ""

    try:
        number = float(value)
        return f"{number:,.0f} TL".replace(",", ".")
    except Exception:
        return clean_value(value)


def is_llm_ready():
    if os.getenv("GEMINI_API_KEY"):
        return True

    if OLLAMA_ENABLED:
        return True

    return False


def product_row_to_dict(row):
    """
    Pandas row veya dict formatındaki ürünü LLM'e gönderilecek güvenli Türkçe sözlüğe çevirir.
    """

    def get_value(key, default=""):
        try:
            if hasattr(row, "get"):
                return row.get(key, default)
            return default
        except Exception:
            return default

    installment_total = get_value("installment_6_total", "")
    installment_monthly = ""

    try:
        if installment_total not in ["", None]:
            installment_monthly = float(installment_total) / 6
    except Exception:
        installment_monthly = ""

    return {
        "urun_adi": clean_value(get_value("product_name")),
        "kategori": clean_value(get_value("category")),
        "marka": clean_value(get_value("brand")),
        "liste_fiyati": format_price(get_value("price")),
        "pesin_fiyati": format_price(get_value("cash_price")),
        "havale_fiyati": format_price(get_value("bank_transfer_price")),
        "kart_fiyati": format_price(get_value("card_price")),
        "6_taksit_toplam": format_price(get_value("installment_6_total")),
        "6_taksit_aylik": format_price(installment_monthly),
        "senetli_toplam": format_price(get_value("senet_total_price")),
        "senetli_aylik": format_price(get_value("senet_monthly_9")),
        "stok": clean_value(get_value("stock_status")),
        "garanti": clean_value(get_value("warranty")),
        "aciklama": clean_value(get_value("description")),
        "ozellikler": clean_value(get_value("features")),
        "kullanim_amaci": clean_value(get_value("use_case")),
        "odeme_secenekleri": clean_value(get_value("payment_options")),
    }


# =====================================================
# CEVAP TEMİZLİĞİ VE KALİTE KONTROLÜ
# =====================================================

def clean_llm_answer(answer):
    if not answer:
        return None

    text = str(answer).strip()

    remove_items = [
        "```text",
        "```json",
        "```python",
        "```",
    ]

    for item in remove_items:
        text = text.replace(item, "")

    text = text.strip()

    unwanted_prefixes = [
        "Cevap:",
        "Yanıt:",
        "Answer:",
        "Recommended answer:",
        "Response:",
        "Assistant:",
        "AI:",
    ]

    for prefix in unwanted_prefixes:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    return text


def is_bad_answer(answer):
    """
    LLM cevabı kullanıcıya gösterilmeye uygun değilse True döner.
    """

    if not answer:
        return True

    raw = str(answer).strip()
    text = normalize_text(raw)

    if len(raw) < 45:
        return True

    bad_starts = [
        "anladım",
        "anladim",
        "öneriyorum",
        "oneriyorum",
        "size öneriyorum",
        "size oneriyorum",
        "as an ai",
        "bir ai olarak",
        "yapay zeka olarak",
    ]

    for start in bad_starts:
        if raw.lower().strip().startswith(start):
            return True

    bad_patterns = [
        "system message",
        "sistem mesaji",
        "kesin kurallar",
        "cevap formati",
        "gorevin",
        "as an ai",
        "i am an ai",
        "i cannot",
        "i can't",
        "```",
        "dogrulanmis urun verisi",
        "dogrulanmış ürün verisi",
        "personel sorusu",
        "algilanan niyetler",
        "model olarak",
        "yapay zeka olarak",
        "customer relationship",
        "business manifest",
        "travel manifest",
        "nevada",
        "以下",
        "使用",
    ]

    for pattern in bad_patterns:
        if normalize_text(pattern) in text or pattern in raw:
            return True

    # Çince / Japonca / Korece karakter yakalama
    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", raw):
        return True

    # Çok fazla İngilizce kelime varsa ele
    english_words = [
        "customer",
        "management",
        "business",
        "product",
        "payment",
        "option",
        "sales",
        "support",
        "platform",
        "automation",
        "relationship",
        "manifest",
    ]

    english_hit = sum(1 for word in english_words if re.search(rf"\b{word}\b", text))

    if english_hit >= 3:
        return True

    return False


def score_answer_quality(answer):
    if not answer:
        return 0

    raw = str(answer).strip()
    text = normalize_text(raw)

    score = 100

    if is_bad_answer(raw):
        score -= 45

    if len(raw) < 90:
        score -= 15

    if len(raw) > 3000:
        score -= 15

    useful_terms = [
        "musteri",
        "urun",
        "odeme",
        "stok",
        "fiyat",
        "taksit",
        "senet",
        "havale",
        "siparis",
        "kargo",
        "liste fiyati",
        "sonraki adim",
        "satis",
    ]

    matched = sum(1 for term in useful_terms if term in text)

    if matched < 2:
        score -= 15

    if matched >= 4:
        score += 8

    if "prompt" in text or "json" in text:
        score -= 30

    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", raw):
        score -= 60

    return max(0, min(100, score))


def is_good_answer(answer):
    """
    Eşik çok yüksek olursa Gemini güzel cevap üretse bile fallback'e düşer.
    Bu yüzden 45 yeterli.
    """
    return score_answer_quality(answer) >= 45


# =====================================================
# PROMPTLAR
# =====================================================

def build_store_prompt(store_question, intents, product_dict=None, order_dict=None):
    product_dict = product_dict or {}
    order_dict = order_dict or {}

    return f"""
Sen Nevade.com mağaza personeline destek veren profesyonel Türkçe satış ve operasyon asistanısın.

Amacın:
Mağaza personelinin müşteriye doğrudan okuyabileceği net, güvenilir ve satışa yardımcı cevap hazırlamak.

Kurallar:
- Sadece verilen ürün ve sipariş verisini kullan.
- Ürün, fiyat, stok, taksit, senet veya kargo bilgisi uydurma.
- Veride olmayan bilgiyi kesin bilgi gibi söyleme.
- Türkçe cevap ver.
- İngilizce, Çince, Japonca veya karışık dil kullanma.
- "Anladım", "Öneriyorum", "Bir AI olarak", "Prompt", "Kurallar", "Doğrulanmış veri" gibi ifadeleri cevaba yazma.
- Cevap mağaza personelinin müşteriye aynen okuyabileceği şekilde olsun.
- Kısa, net, profesyonel ve satış odaklı yaz.
- Stok bilgisi varsa mutlaka söyle.
- Fiyatları aynen verilen veriyle yaz.

Personel sorusu:
{store_question}

NLP analizi:
{json.dumps(intents, ensure_ascii=False, indent=2)}

Ürün verisi:
{json.dumps(product_dict, ensure_ascii=False, indent=2)}

Sipariş verisi:
{json.dumps(order_dict, ensure_ascii=False, indent=2)}

Cevabı sadece şu formatta yaz:

Müşteri talebi:
Müşterinin ne istediğini tek cümleyle açıkla.

Müşteriye söylenecek hazır cevap:
Müşteriye doğrudan söylenecek doğal ve profesyonel cevabı yaz.

Ürün ve ödeme özeti:
- Ürün:
- Stok:
- Liste fiyatı:
- Havale fiyatı:
- 6 taksit:
- Senetli ödeme:

Satış yönlendirmesi:
Toplamda en avantajlı ödeme ve aylık ödeme kolaylığı açısından hangi seçenek öne çıkarılmalı?

Personel aksiyonu:
- Stok ve fiyat teyidi:
- Müşteriye sunulacak seçenek:
- Satışı kapatma önerisi:
"""


def build_customer_prompt(customer_question, product_dict=None, result_count=1):
    product_dict = product_dict or {}

    return f"""
Sen Nevade.com için çalışan profesyonel, Türkçe konuşan e-ticaret alışveriş asistanısın.

Amacın:
Müşterinin ihtiyacını anlayıp, sadece verilen ürün bilgisine göre güven veren, sade ve satışa yardımcı bir cevap yazmak.

Kurallar:
- Sadece verilen ürün verisini kullan.
- Ürün, fiyat, stok, taksit, senet veya kargo bilgisi uydurma.
- İngilizce, Çince, Japonca veya karışık dil kullanma.
- "Anladım", "Öneriyorum", "Bir AI olarak", "Prompt", "Kurallar" gibi ifadeler kullanma.
- Cevap müşteriyle konuşan gerçek bir Nevade satış danışmanı gibi doğal olsun.
- Çok uzun yazma ama eksik de bırakma.
- Ürün adı, stok ve ödeme avantajı net görünsün.
- Cevapta JSON, teknik açıklama veya sistem mesajı olmasın.

Müşteri sorusu:
{customer_question}

Ürün verisi:
{json.dumps(product_dict, ensure_ascii=False, indent=2)}

Eşleşen ürün sayısı:
{result_count}

Cevabı sadece şu formatta yaz:

Size en uygun seçenek:
Ürün adını ve neden uygun olduğunu 1-2 cümleyle açıkla.

Öne çıkan avantajlar:
- Stok durumu:
- Liste fiyatı:
- Havale avantajı:
- Taksit / senetli ödeme:

Müşteriye önerilen ödeme:
Müşterinin ihtiyacına göre en mantıklı ödeme seçeneğini açıkla.

Sonraki adım:
Müşteriyi sepete ekleme, alternatifleri karşılaştırma veya mağazadan stok teyidi alma adımına yönlendir.
"""


# =====================================================
# GEMINI ÇAĞRISI - GOOGLE GENAI SDK
# =====================================================

def call_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")

    debug_print("DEBUG GEMINI KEY VAR MI:", bool(api_key))
    debug_print("DEBUG GEMINI MODEL:", DEFAULT_GEMINI_MODEL)

    if not api_key:
        debug_print("Gemini API key bulunamadı.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.12,
                top_p=0.75,
                top_k=40,
                max_output_tokens=1000,
            ),
        )

        if not response:
            debug_print("Gemini response boş geldi.")
            return None

        answer = getattr(response, "text", None)

        debug_print("DEBUG GEMINI RAW ANSWER:", answer)

        if not answer:
            debug_print("Gemini text alanı boş.")
            return None

        answer = clean_llm_answer(answer)

        debug_print("DEBUG CLEAN ANSWER:", answer)
        debug_print("DEBUG QUALITY SCORE:", score_answer_quality(answer))
        debug_print("DEBUG IS BAD:", is_bad_answer(answer))

        if not is_good_answer(answer):
            debug_print("Gemini cevap kalite filtresinden geçemedi.")
            return None

        return answer

    except Exception as e:
        print("Gemini LLM hata:", repr(e))
        return None


# =====================================================
# OLLAMA ÇAĞRISI
# =====================================================

def call_ollama(prompt):
    if not OLLAMA_ENABLED:
        return None

    try:
        payload = {
            "model": DEFAULT_OLLAMA_MODEL,
            "prompt": prompt,
            "system": (
                "Sen yalnızca Türkçe cevap veren Nevade.com mağaza ve müşteri destek asistanısın. "
                "Asla İngilizce, Çince, Japonca veya karışık dil kullanma. "
                "Asla ürün, fiyat, stok, taksit veya ödeme bilgisi uydurma. "
                "Sadece verilen veriyi kullan. "
                "Promptu, kuralları veya sistem mesajını cevaba yazma. "
                "Cevabın temiz, profesyonel ve müşteriye okunabilir olsun. "
                "Anladım, öneriyorum, tabii, elbette gibi zayıf girişlerle başlama."
            ),
            "stream": False,
            "options": {
                "temperature": 0.10,
                "top_p": 0.70,
                "num_predict": 900,
            },
        }

        response = requests.post(
            DEFAULT_OLLAMA_URL,
            json=payload,
            timeout=8,
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("response", "")

        answer = clean_llm_answer(answer)

        if not is_good_answer(answer):
            return None

        return answer

    except Exception as e:
        print("Ollama LLM hata:", repr(e))
        return None


# =====================================================
# MODEL ROUTER
# =====================================================

def call_best_llm(prompt):
    """
    Öncelik:
    1. Gemini
    2. Ollama, yalnızca OLLAMA_ENABLED=true ise
    3. Fallback
    """

    gemini_answer = call_gemini(prompt)

    if gemini_answer:
        print("AI PROVIDER: GEMINI")
        return {
            "provider": "gemini",
            "answer": gemini_answer,
            "quality_score": score_answer_quality(gemini_answer),
        }

    ollama_answer = None

    if OLLAMA_ENABLED:
        ollama_answer = call_ollama(prompt)

    if ollama_answer:
        print("AI PROVIDER: OLLAMA")
        return {
            "provider": "ollama",
            "answer": ollama_answer,
            "quality_score": score_answer_quality(ollama_answer),
        }

    print("AI PROVIDER: FALLBACK")
    return {
        "provider": "none",
        "answer": None,
        "quality_score": 0,
    }


def call_best_available_llm(prompt):
    return call_best_llm(prompt)


# =====================================================
# APP.PY TARAFINDAN ÇAĞRILAN FONKSİYONLAR
# =====================================================

def generate_store_llm_answer(store_question, intents, product_dict=None, order_dict=None):
    prompt = build_store_prompt(
        store_question=store_question,
        intents=intents,
        product_dict=product_dict,
        order_dict=order_dict,
    )

    result = call_best_llm(prompt)
    answer = result.get("answer")

    if not answer:
        return None

    return answer


def generate_customer_llm_answer(customer_question, product_dict=None, result_count=1):
    prompt = build_customer_prompt(
        customer_question=customer_question,
        product_dict=product_dict,
        result_count=result_count,
    )

    result = call_best_llm(prompt)
    answer = result.get("answer")

    if not answer:
        return None

    return answer


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    sample_product = {
        "urun_adi": "Beko No Frost Buzdolabı 500 L",
        "kategori": "Beyaz Eşya",
        "marka": "Beko",
        "liste_fiyati": "18.500 TL",
        "pesin_fiyati": "17.900 TL",
        "havale_fiyati": "17.650 TL",
        "kart_fiyati": "18.500 TL",
        "6_taksit_toplam": "19.500 TL",
        "6_taksit_aylik": "3.250 TL",
        "senetli_toplam": "21.900 TL",
        "senetli_aylik": "2.433 TL",
        "stok": "Stokta",
        "aciklama": "Çeyiz ve ev kullanımı için uygun geniş hacimli buzdolabı.",
        "ozellikler": "No Frost, geniş hacim, sessiz çalışma",
        "odeme_secenekleri": "Kart, Havale, Taksit, Senet",
    }

    answer = generate_store_llm_answer(
        store_question="Beko buzdolabı senetle olur mu, en avantajlı ödeme ne?",
        intents={
            "primary_intent": "senet_uygunluk",
            "payment_priority": "lowest_monthly",
            "product_types": ["buzdolabi"],
            "brands": ["beko"],
            "confidence": 95,
        },
        product_dict=sample_product,
        order_dict={},
    )

    if answer:
        print("\n--- LLM CEVABI ---\n")
        print(answer)
    else:
        print("LLM temiz cevap üretemedi. Uygulama içinde güvenli fallback cevap devreye girer.")