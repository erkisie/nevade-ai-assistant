import os
import json

from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.5").strip()
        self.enabled = bool(self.api_key)
        self.client = None

        if self.enabled:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None
                self.enabled = False

    def is_enabled(self):
        return self.enabled and self.client is not None

    def build_context(self, user_query, query_info, products):
        clean_products = []

        for product in products[:5]:
            clean_products.append({
                "product_id": product.get("product_id"),
                "product_name": product.get("product_name"),
                "category": product.get("category"),
                "brand": product.get("brand"),
                "price": product.get("price"),
                "cash_price": product.get("cash_price"),
                "bank_transfer_price": product.get("bank_transfer_price"),
                "card_price": product.get("card_price"),
                "installment_3_total": product.get("installment_3_total"),
                "installment_6_total": product.get("installment_6_total"),
                "installment_9_total": product.get("installment_9_total"),
                "senet_total_price": product.get("senet_total_price"),
                "senet_monthly_9": product.get("senet_monthly_9"),
                "stock_status": product.get("stock_status"),
                "match_label": product.get("match_label"),
                "reason": product.get("reason"),
                "specs": product.get("specs", {})
            })

        return {
            "user_query": user_query,
            "detected_query_info": query_info,
            "recommended_products": clean_products
        }

    def generate_shopping_answer(self, user_query, query_info, products, fallback_message):
        if not self.is_enabled():
            return fallback_message

        if not products:
            return fallback_message

        context = self.build_context(user_query, query_info, products)

        system_instructions = """
Sen Nevade.com için çalışan Türkçe bir AI alışveriş asistanısın.

Kurallar:
- Sadece verilen ürün datasına dayan.
- Verilmeyen ürünü, fiyatı, kampanyayı veya stok bilgisini uydurma.
- En üstteki ürün motor tarafından en uygun ürün olarak seçilmiştir.
- Cevap doğal, güvenilir, profesyonel ve kısa-orta uzunlukta olsun.
- Product ID bilgisini gerekirse belirt.
- Ödeme tercihi varsa özellikle açıkla: senet, havale, peşin, taksit.
- Ucuz olanı otomatik en iyi diye gösterme; kullanım, enerji, kapasite, performans gibi kriterleri de açıkla.
- Cevabı şu yapıda ver:
  1) Net öneri
  2) Neden önerildi
  3) Ödeme/fiyat yorumu
  4) Alternatif varsa kısa alternatif
- Teknik terimleri sade anlat.
"""

        user_input = f"""
Kullanıcı sorusu:
{user_query}

Motor çıktısı JSON:
{json.dumps(context, ensure_ascii=False, indent=2)}

Bu verilere göre kullanıcıya Nevade alışveriş asistanı gibi cevap yaz.
"""

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_instructions,
                input=user_input
            )

            text = getattr(response, "output_text", None)

            if text and str(text).strip():
                return text.strip()

            return fallback_message

        except Exception:
            return fallback_message