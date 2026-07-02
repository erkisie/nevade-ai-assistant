import os
import json
import traceback
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_PACKAGE_READY = True
except Exception as e:
    print("google-generativeai import error:", e)
    genai = None
    GEMINI_PACKAGE_READY = False


def get_gemini_key():
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_gemini_model():
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()


def is_llm_ready():
    key = get_gemini_key()
    return GEMINI_PACKAGE_READY and bool(key)


def compact_money(value):
    try:
        value = float(value)
        if value <= 0:
            return "-"
        return f"{value:,.0f} TL".replace(",", ".")
    except Exception:
        return "-"


def product_row_to_dict(row):
    return {
        "urun_adi": str(row.get("product_name", "")),
        "kategori": str(row.get("category", "")),
        "marka": str(row.get("brand", "")),
        "liste_fiyati": compact_money(row.get("price", 0)),
        "pesin_fiyat": compact_money(row.get("cash_price", 0)),
        "havale_fiyati": compact_money(row.get("bank_transfer_price", 0)),
        "kart_fiyati": compact_money(row.get("card_price", 0)),
        "3_taksit_toplam": compact_money(row.get("installment_3_total", 0)),
        "6_taksit_toplam": compact_money(row.get("installment_6_total", 0)),
        "9_taksit_toplam": compact_money(row.get("installment_9_total", 0)),
        "senetli_toplam": compact_money(row.get("senet_total_price", 0)),
        "senetli_aylik": compact_money(row.get("senet_monthly_9", 0)),
        "renk": str(row.get("color", "")),
        "stok": str(row.get("stock_status", "")),
        "islemci": str(row.get("processor", "")),
        "ram": str(row.get("ram", "")),
        "depolama": str(row.get("storage", "")),
        "ekran": str(row.get("screen_size", "")),
        "kapasite": str(row.get("capacity", "")),
        "enerji_sinifi": str(row.get("energy_class", "")),
        "garanti": str(row.get("warranty", "")),
        "odeme_secenekleri": str(row.get("payment_options", "")),
        "kullanim_amaci": str(row.get("use_case", "")),
        "ozellikler": str(row.get("features", "")),
        "aciklama": str(row.get("description", ""))
    }


def build_customer_prompt(user_query, query_info, products):
    product_list = [product_row_to_dict(row) for row in products]

    return f"""
Sen Nevade.com için çalışan müşteri odaklı bir AI alışveriş asistanısın.

Müşteri doğal dilde bir alışveriş ihtiyacı yazıyor. Senin görevin, verilen ürün listesinden en uygun ürünü müşteriyle konuşan satış danışmanı gibi önermek.

Kesin kurallar:
- Sadece verilen ürün verilerine dayan.
- Ürün verisinde olmayan bilgiyi uydurma.
- "Kategori algıladım", "ürün tipi algıladım" gibi teknik ifadeler kullanma.
- Robot gibi değil, doğal ve müşteri odaklı konuş.
- Cevap kısa, anlaşılır ve güven verici olsun.
- Eğer müşteri sadece bütçe yazdıysa ve kategori belirtmediyse ürün önermek yerine hangi ürün grubunu düşündüğünü sor.
- Havale, taksit veya senet geçiyorsa ödeme avantajını doğal anlat.
- Senetli toplam ödeme daha yüksekse dürüstçe belirt.
- Stok bilgisi varsa belirt.
- Alternatif ürünleri doğal şekilde söyle.
- Cevap Türkçe olsun.

Müşteri mesajı:
{user_query}

Sistemin çıkardığı niyet:
{json.dumps(query_info, ensure_ascii=False, indent=2)}

Önerilen ürünler:
{json.dumps(product_list, ensure_ascii=False, indent=2)}

Cevap formatı:
- 2 veya 3 kısa paragraf yaz.
- En uygun ürünü öner.
- Ödeme avantajını açıkla.
- Alternatifleri belirt.
- Sonunda kısa yönlendirme cümlesi ekle.

Şimdi müşteriye cevap ver.
"""


def build_store_prompt(store_question, intents, product=None, order=None):
    return f"""
Sen Nevade.com mağaza personeline destek veren iç operasyon AI asistanısın.

Kurallar:
- Kısa, net ve uygulanabilir cevap ver.
- Sadece verilen ürün veya sipariş bilgisine dayan.
- Bilgi yoksa "bu bilgi sistemde görünmüyor, merkezden kontrol edilmelidir" de.
- Mağaza personeline müşteriye nasıl cevap verebileceğini de kısa şekilde söyle.
- Cevap Türkçe olsun.

Mağaza sorusu:
{store_question}

Algılanan konu:
{json.dumps(intents, ensure_ascii=False, indent=2)}

Eşleşen ürün:
{json.dumps(product, ensure_ascii=False, indent=2) if product else "Yok"}

Eşleşen sipariş:
{json.dumps(order, ensure_ascii=False, indent=2) if order else "Yok"}

Şimdi mağaza personeline cevap ver.
"""


def call_gemini(prompt, max_tokens=650, temperature=0.45):
    if not GEMINI_PACKAGE_READY:
        print("Gemini package is not installed.")
        return None

    api_key = get_gemini_key()
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return None

    model_name = get_gemini_model()

    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )

        response = model.generate_content(prompt)

        print("Gemini model used:", model_name)
        print("Gemini raw response:", response)

        if response is None:
            print("Gemini response is None")
            return None

        if hasattr(response, "text"):
            try:
                text = response.text
                if text:
                    return text.strip()
            except Exception as e:
                print("response.text error:", e)

        try:
            candidates = getattr(response, "candidates", [])
            if candidates:
                parts = candidates[0].content.parts
                if parts and hasattr(parts[0], "text"):
                    return parts[0].text.strip()
        except Exception as e:
            print("candidate parse error:", e)

        print("Gemini returned no usable text.")
        return None

    except Exception as error:
        print("Gemini error:", error)
        traceback.print_exc()
        return None


def generate_customer_llm_answer(user_query, query_info, result_df):
    if result_df is None or result_df.empty:
        return None

    products = []
    for _, row in result_df.head(5).iterrows():
        products.append(row)

    prompt = build_customer_prompt(
        user_query=user_query,
        query_info=query_info,
        products=products
    )

    return call_gemini(
        prompt=prompt,
        max_tokens=700,
        temperature=0.45
    )


def generate_store_llm_answer(store_question, intents, product_dict=None, order_dict=None):
    prompt = build_store_prompt(
        store_question=store_question,
        intents=intents,
        product=product_dict,
        order=order_dict
    )

    return call_gemini(
        prompt=prompt,
        max_tokens=500,
        temperature=0.30
    )