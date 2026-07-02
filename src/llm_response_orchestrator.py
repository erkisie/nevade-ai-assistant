import json
import pandas as pd

from src.customer_intelligence_engine import safe_number, money
from src.answer_formatter_engine import format_answer

# =====================================================
# LLM RESPONSE ORCHESTRATOR
# LLM sadece güvenli veriyi müşteri/personel diliyle yazar
# Ürün uydurmaz, fiyat uydurmaz, veri dışına çıkmaz
# =====================================================


try:
    from src.llm_provider_router import call_best_available_llm
except Exception:
    call_best_available_llm = None


def clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def product_to_safe_dict(row):
    """
    LLM'e gönderilecek güvenli ürün verisi.
    Fazla kolon gönderilmez, ürün uydurma riski azaltılır.
    """

    return {
        "product_id": clean_text(row.get("product_id", "")),
        "product_name": clean_text(row.get("product_name", "")),
        "category": clean_text(row.get("category", "")),
        "brand": clean_text(row.get("brand", "")),
        "price": money(row.get("price", 0)),
        "cash_price": money(row.get("cash_price", 0)),
        "bank_transfer_price": money(row.get("bank_transfer_price", 0)),
        "card_price": money(row.get("card_price", 0)),
        "installment_6_monthly": money(safe_number(row.get("installment_6_total", 0)) / 6)
        if safe_number(row.get("installment_6_total", 0)) > 0
        else "-",
        "senet_total_price": money(row.get("senet_total_price", 0)),
        "senet_monthly_9": money(row.get("senet_monthly_9", 0)),
        "stock_status": clean_text(row.get("stock_status", "")),
        "package_group": clean_text(row.get("package_group", "")),
        "description": clean_text(row.get("description", "")),
        "features": clean_text(row.get("features", "")),
        "use_case": clean_text(row.get("use_case", "")),
    }


def products_to_safe_list(result_df, max_items=6):
    if result_df is None or not isinstance(result_df, pd.DataFrame) or result_df.empty:
        return []

    safe_products = []

    for _, row in result_df.head(max_items).iterrows():
        safe_products.append(product_to_safe_dict(row))

    return safe_products


def is_bad_llm_answer(answer, safe_products):
    """
    LLM cevabı müşteriye gösterilmeye uygun mu kontrol eder.
    Küçük modeller İngilizce karıştırabilir, ürün uydurabilir veya eksik cevap verebilir.
    Böyle durumlarda fallback kullanılır.
    """

    if answer is None:
        return True

    answer = str(answer).strip()

    if len(answer) < 30:
        return True

    lower_answer = answer.lower()
    prompt_leak_phrases = [
        "sen nevade.com için çalışan",
        "cevap formatı",
        "dil kuralı",
        "kesin kurallar",
        "görevin",
        "veri:",
        "müşteriye doğal",
        "aşağıdaki gibi bir cevap",
        "tek ürün önerme",
        "paket grup grup",
        "ingilizce kelime",
        "cevabın tamamen türkçe",
    ]

    for phrase in prompt_leak_phrases:
        if phrase in lower_answer:
            return True
    bad_phrases = [
        "ürün bilgisi bulunamadı",
        "veri yok",
        "bilmiyorum",
        "emin değilim",
        "listeye erişemiyorum",
        "fiyat bilgisi yok",
        "i don't know",
        "i cannot",
        "i can't",
        "as an ai",
    ]

    for phrase in bad_phrases:
        if phrase in lower_answer:
            return True

    english_bad_words = [
        "cart",
        "expensive",
        "alternatives",
        "customer",
        "payment options",
        "your budget",
        "anlay",
        "recommendation",
        "assistant",
        "product list",
    ]

    for word in english_bad_words:
        if word in lower_answer:
            return True

    # Cevapta güvenli ürün listesinden en az bir ürün geçmeli.
    # Eğer ürün listesi varsa ve LLM hiçbir ürün adını yazmadıysa cevap riskli.
    if safe_products:
        product_names = [
            str(item.get("product_name", "")).strip().lower()
            for item in safe_products
            if item.get("product_name")
        ]

        if product_names:
            mentioned = any(name in lower_answer for name in product_names)

            if not mentioned:
                return True

    # Ürün listesinde olmayan marka/ürün uydurma riskini azaltmak için
    # temel kontrol: cevap çok genel kalmışsa reddet.
    too_generic_phrases = [
        "size uygun ürünleri listeledim",
        "aşağıdaki ürünleri inceleyebilirsiniz",
        "bazı seçenekler sunabilirim",
    ]

    if safe_products:
        generic_count = sum(1 for phrase in too_generic_phrases if phrase in lower_answer)

        if generic_count > 0 and len(answer) < 180:
            return True

    return False


def build_customer_prompt(orchestrator_result):
    """
    Müşteri tarafı için LLM promptu.
    """

    decision = orchestrator_result.get("decision", "")
    analysis = orchestrator_result.get("customer_analysis") or orchestrator_result.get("analysis", {})
    analysis_summary = orchestrator_result.get("analysis_summary", "")
    cart_summary = orchestrator_result.get("cart_summary", {})
    fallback_answer = orchestrator_result.get("answer", "") or orchestrator_result.get("fallback_answer", "")

    result_df = orchestrator_result.get("result_df", pd.DataFrame())
    safe_products = products_to_safe_list(result_df)

    payload = {
        "decision": decision,
        "analysis_summary": analysis_summary,
        "customer_analysis": analysis,
        "cart_summary": cart_summary,
        "safe_products": safe_products,
        "safe_fallback_answer": fallback_answer,
    }

    prompt = f"""
Sen Nevade.com için çalışan Türkçe konuşan kişisel alışveriş asistanısın.

DİL KURALI:
- Cevabın tamamen Türkçe olmalı.
- İngilizce kelime veya cümle kullanma.
- "cart", "expensive", "alternatives", "customer", "payment options" gibi İngilizce ifadeler yazma.

ROLÜN:
Müşteriye satış danışmanı gibi yardımcı ol.
Müşteriyi sepetten vazgeçirmemeye çalış.
Müşteriye güven veren, kısa ve net cevap ver.

KESİN KURALLAR:
- Sadece VERİ alanındaki güvenli ürünleri kullan.
- Güvenli ürün listesinde olmayan ürün adı yazma.
- Fiyat, stok, taksit, senet ve havale bilgisini uydurma.
- Teknik terim kullanma: NLP, embedding, semantic, model, skor, algoritma deme.
- Çok uzun yazma.
- Müşteriye baskı yapma.
- Cevabın sonunda bir sonraki adımı öner.

KARARA GÖRE DAVRANIŞ:
- CART_RESCUE: Müşterinin ödeme/limit sorunu yaşadığını anla. Daha uygun alternatifleri ve ödeme avantajını anlat.
- BUDGET_OPTIMIZED: Bütçe aşımı nedeniyle paketin optimize edildiğini açıkla.
- BUDGET_PARTIALLY_OPTIMIZED: Paket kısmen optimize edildi ama hâlâ bütçeyi aşıyorsa dürüstçe söyle.
- PACKAGE_RECOMMENDATION: Tek ürün önerme, paketi grup grup anlat.
- PAYMENT_HELP: Havale, taksit, senet gibi ödeme seçeneklerini anlaşılır şekilde yaz.
- PRODUCT_RECOMMENDATION: Ürünleri müşterinin ihtiyacına göre öner.

VERİ:
{json.dumps(payload, ensure_ascii=False, indent=2)}

CEVAP FORMATI:
Kısa giriş cümlesi yaz.
Sonra ürünleri veya çözümü madde madde yaz.
En sonda müşteriye şu tarz bir sonraki adım öner:
- "İsterseniz en düşük fiyatlı seçeneklere göre yeniden sıralayabilirim."
- "İsterseniz senetli ödeme seçeneğine göre yeniden düzenleyebilirim."
- "İsterseniz bu ürünleri karşılaştırabilirim."
"""

    return prompt, safe_products, fallback_answer


def build_store_prompt(orchestrator_result):
    """
    Mağaza personeli tarafı için LLM promptu.
    """

    decision = orchestrator_result.get("decision", "")
    analysis = orchestrator_result.get("customer_analysis") or orchestrator_result.get("analysis", {})
    analysis_summary = orchestrator_result.get("analysis_summary", "")
    fallback_answer = orchestrator_result.get("answer", "") or orchestrator_result.get("fallback_answer", "")

    result_df = orchestrator_result.get("result_df", pd.DataFrame())
    safe_products = products_to_safe_list(result_df)

    payload = {
        "decision": decision,
        "analysis_summary": analysis_summary,
        "customer_analysis": analysis,
        "safe_products": safe_products,
        "safe_fallback_answer": fallback_answer,
    }

    prompt = f"""
Sen Nevade.com mağaza personeli için çalışan Türkçe operasyon asistanısın.

DİL KURALI:
- Tamamen Türkçe cevap ver.
- İngilizce kelime veya cümle kullanma.

GÖREVİN:
Mağaza personeline kısa, net, aksiyon odaklı cevap yaz.

KESİN KURALLAR:
- Sadece VERİ alanındaki güvenli ürünleri kullan.
- Ürün, fiyat, stok veya ödeme bilgisi uydurma.
- Müşteriye söylenecek cevabı ayrı yaz.
- Personelin yapması gereken aksiyonu ayrı yaz.
- Teknik terim kullanma.
- Gereksiz uzun pazarlama metni yazma.
- Personeli güncel stok ve ödeme koşullarını teyit etmeye yönlendir.

VERİ:
{json.dumps(payload, ensure_ascii=False, indent=2)}

CEVAP FORMATI:
Müşteriye cevap:
...

Personel aksiyonu:
...
"""

    return prompt, safe_products, fallback_answer


def call_safe_llm(prompt):
    """
    Ollama/Gemini/Fallback router üzerinden güvenli LLM çağrısı yapar.
    Gemini quota dolarsa traceback basmaz, fallback'e döner.
    """

    if call_best_available_llm is None:
        return None

    result = call_best_available_llm(prompt)

    answer = result.get("answer")
    provider = result.get("provider", "Fallback")

    if answer:
        print(f"LLM Provider Used: {provider}")
        return str(answer).strip()

    print("LLM Provider Used: Fallback")
    return None

def generate_safe_customer_response(orchestrator_result):
    """
    Müşteri tarafı nihai cevap.
    Küçük lokal model prompt sızdırabildiği için müşteri ekranında
    öncelik net ve güvenli formatter cevabındadır.
    """

    formatted_answer = format_answer(orchestrator_result)
    return formatted_answer

def generate_safe_store_response(orchestrator_result):
    """
    Mağaza personeli tarafı nihai cevap.
    """

    formatted_fallback = format_answer(orchestrator_result)

    prompt, safe_products, _ = build_store_prompt(orchestrator_result)

    llm_answer = call_safe_llm(prompt)

    if is_bad_llm_answer(llm_answer, safe_products):
        return formatted_fallback

    return llm_answer


def generate_response(orchestrator_result, mode="customer"):
    """
    Dışarıdan çağrılacak tek fonksiyon.
    mode:
    - customer
    - store
    """

    if mode == "store":
        return generate_safe_store_response(orchestrator_result)

    return generate_safe_customer_response(orchestrator_result)