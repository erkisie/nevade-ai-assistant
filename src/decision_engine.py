from src.utils import normalize_text, safe_number, money, extract_first_number


class DecisionEngine:
    def energy_rank(self, value):
        value = str(value).upper().replace(" ", "")

        ranks = {
            "A+++": 5,
            "A++": 4,
            "A+": 3,
            "A": 2,
            "B": 1
        }

        return ranks.get(value, 0)

    def capacity_value(self, value):
        return extract_first_number(value)

    def ram_value(self, value):
        return extract_first_number(value)

    def storage_value(self, value):
        text = normalize_text(value)
        number = extract_first_number(value)

        if "tb" in text:
            return number * 1024

        return number

    def payment_analysis(self, row):
        price = safe_number(row.get("price", 0))
        cash = safe_number(row.get("cash_price", 0))
        havale = safe_number(row.get("bank_transfer_price", 0))
        card = safe_number(row.get("card_price", 0))
        installment_3 = safe_number(row.get("installment_3_total", 0))
        installment_6 = safe_number(row.get("installment_6_total", 0))
        installment_9 = safe_number(row.get("installment_9_total", 0))
        senet_total = safe_number(row.get("senet_total_price", 0))
        senet_monthly = safe_number(row.get("senet_monthly_9", 0))

        candidates = []

        if cash > 0:
            candidates.append(("Peşin", cash))

        if havale > 0:
            candidates.append(("Havale", havale))

        if card > 0:
            candidates.append(("Kart", card))

        if installment_3 > 0:
            candidates.append(("3 Taksit", installment_3))

        if installment_6 > 0:
            candidates.append(("6 Taksit", installment_6))

        if installment_9 > 0:
            candidates.append(("9 Taksit", installment_9))

        if senet_total > 0:
            candidates.append(("Senet", senet_total))

        if not candidates:
            return {
                "best_method": "Liste fiyatı",
                "best_total": price,
                "senet_total": senet_total,
                "senet_monthly_9": senet_monthly,
                "advice": "Bu ürün için ödeme alternatifi bilgisi sınırlı."
            }

        best_method, best_total = min(candidates, key=lambda item: item[1])

        if senet_total > 0:
            senet_difference = senet_total - best_total
        else:
            senet_difference = 0

        if senet_total > 0 and senet_difference > 0:
            advice = (
                f"En avantajlı ödeme seçeneği {best_method} ({money(best_total)}). "
                f"Senetli toplam {money(senet_total)} olduğu için senet ile en avantajlı ödeme arasında "
                f"{money(senet_difference)} fark oluşuyor."
            )
        else:
            advice = (
                f"Bu ürün için en avantajlı ödeme seçeneği {best_method}: {money(best_total)}."
            )

        return {
            "best_method": best_method,
            "best_total": best_total,
            "senet_total": senet_total,
            "senet_monthly_9": senet_monthly,
            "senet_difference": senet_difference,
            "advice": advice
        }

    def feature_score(self, row, priority):
        if priority == "capacity":
            capacity = self.capacity_value(row.get("capacity", ""))
            return min(capacity / 600, 1.0) if capacity > 0 else 0.5

        if priority == "energy":
            rank = self.energy_rank(row.get("energy_class", ""))
            return min(rank / 5, 1.0) if rank > 0 else 0.5

        if priority == "performance":
            ram = self.ram_value(row.get("ram", ""))
            storage = self.storage_value(row.get("storage", ""))

            score = 0.35

            if ram >= 16:
                score += 0.30
            elif ram >= 8:
                score += 0.20

            if storage >= 512:
                score += 0.30
            elif storage >= 256:
                score += 0.20

            processor = normalize_text(row.get("processor", ""))

            if "i7" in processor or "m2" in processor or "ryzen 7" in processor:
                score += 0.20
            elif "i5" in processor or "ryzen 5" in processor:
                score += 0.10

            return min(score, 1.0)

        if priority == "usage":
            use_case = normalize_text(row.get("use_case", ""))
            features = normalize_text(row.get("features", ""))

            score = 0.45

            if "gunluk" in use_case or "pratik" in features:
                score += 0.15

            if "aile" in use_case or "ceyiz" in use_case:
                score += 0.15

            if "ogrenci" in use_case:
                score += 0.15

            if "sessiz" in features or "hafif" in features or "genis" in features:
                score += 0.15

            return min(score, 1.0)

        return 0.65

    def payment_score(self, row, query_info):
        preference = query_info.get("payment_preference")
        price = safe_number(row.get("price", 0))

        if preference == "senet":
            senet_total = safe_number(row.get("senet_total_price", 0))

            if senet_total <= 0:
                return 0.1

            ratio = senet_total / price if price > 0 else 9

            if ratio <= 1.10:
                return 1.0
            if ratio <= 1.20:
                return 0.75
            if ratio <= 1.35:
                return 0.50

            return 0.30

        if preference == "bank_transfer":
            havale = safe_number(row.get("bank_transfer_price", 0))
            if havale > 0 and havale <= price:
                return 1.0
            return 0.4

        if preference == "cash":
            cash = safe_number(row.get("cash_price", 0))
            if cash > 0 and cash <= price:
                return 1.0
            return 0.4

        if preference in ["installment", "installment_3", "installment_6", "installment_9"]:
            if str(row.get("installment_available", "")).lower() == "evet":
                return 1.0
            return 0.3

        return 0.65

    def compare_rows(self, row1, row2, query_info):
        priority = query_info.get("priority", "balanced")

        price1 = safe_number(row1.get("price", 0))
        price2 = safe_number(row2.get("price", 0))

        if priority == "price":
            winner = row1 if price1 <= price2 else row2
            reason = (
                f"Fiyat kriterinde {winner['product_name']} daha avantajlıdır. "
                f"Çünkü liste fiyatı {money(winner['price'])}."
            )

        elif priority == "payment":
            preference = query_info.get("payment_preference")

            if preference == "senet":
                value1 = safe_number(row1.get("senet_total_price", 0))
                value2 = safe_number(row2.get("senet_total_price", 0))
                winner = row1 if value1 <= value2 else row2
                reason = (
                    f"Senetli ödeme açısından {winner['product_name']} daha avantajlıdır. "
                    f"{row1['product_name']} senetli toplamı {money(row1.get('senet_total_price', 0))}, "
                    f"{row2['product_name']} senetli toplamı {money(row2.get('senet_total_price', 0))}."
                )

            elif preference == "bank_transfer":
                value1 = safe_number(row1.get("bank_transfer_price", price1))
                value2 = safe_number(row2.get("bank_transfer_price", price2))
                winner = row1 if value1 <= value2 else row2
                reason = (
                    f"Havale fiyatına göre {winner['product_name']} daha avantajlıdır. "
                    f"{row1['product_name']} havale fiyatı {money(value1)}, "
                    f"{row2['product_name']} havale fiyatı {money(value2)}."
                )

            else:
                score1 = self.payment_score(row1, query_info)
                score2 = self.payment_score(row2, query_info)
                winner = row1 if score1 >= score2 else row2
                reason = (
                    f"Ödeme seçenekleri açısından {winner['product_name']} daha avantajlı görünüyor. "
                    f"{self.payment_analysis(winner)['advice']}"
                )

        elif priority == "capacity":
            cap1 = self.capacity_value(row1.get("capacity", ""))
            cap2 = self.capacity_value(row2.get("capacity", ""))
            winner = row1 if cap1 >= cap2 else row2
            reason = (
                f"Kapasite kriterinde {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} kapasitesi {row1.get('capacity', '-')}, "
                f"{row2['product_name']} kapasitesi {row2.get('capacity', '-')}."
            )

        elif priority == "energy":
            energy1 = self.energy_rank(row1.get("energy_class", ""))
            energy2 = self.energy_rank(row2.get("energy_class", ""))
            winner = row1 if energy1 >= energy2 else row2
            reason = (
                f"Enerji sınıfında {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} enerji sınıfı {row1.get('energy_class', '-')}, "
                f"{row2['product_name']} enerji sınıfı {row2.get('energy_class', '-')}."
            )

        elif priority == "performance":
            score1 = self.feature_score(row1, "performance")
            score2 = self.feature_score(row2, "performance")
            winner = row1 if score1 >= score2 else row2
            reason = (
                f"Performans kriterinde {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} işlemci/RAM/depolama: "
                f"{row1.get('processor', '-')}, {row1.get('ram', '-')}, {row1.get('storage', '-')}; "
                f"{row2['product_name']} işlemci/RAM/depolama: "
                f"{row2.get('processor', '-')}, {row2.get('ram', '-')}, {row2.get('storage', '-')}."
            )

        elif priority == "usage":
            cap1 = self.capacity_value(row1.get("capacity", ""))
            cap2 = self.capacity_value(row2.get("capacity", ""))
            energy1 = self.energy_rank(row1.get("energy_class", ""))
            energy2 = self.energy_rank(row2.get("energy_class", ""))
            usage1 = self.feature_score(row1, "usage")
            usage2 = self.feature_score(row2, "usage")

            total1 = usage1 * 0.35 + (cap1 / 600 if cap1 > 0 else 0.5) * 0.25 + (energy1 / 5 if energy1 > 0 else 0.5) * 0.25 + (1 if price1 <= price2 else 0) * 0.15
            total2 = usage2 * 0.35 + (cap2 / 600 if cap2 > 0 else 0.5) * 0.25 + (energy2 / 5 if energy2 > 0 else 0.5) * 0.25 + (1 if price2 <= price1 else 0) * 0.15

            winner = row1 if total1 >= total2 else row2

            cheaper = row1 if price1 <= price2 else row2

            reason = (
                f"Kullanım kolaylığı açısından {winner['product_name']} daha avantajlı görünüyor. "
                f"Bu karar sadece fiyata göre verilmedi; kapasite, enerji sınıfı, kullanım amacı ve günlük kullanım avantajı birlikte değerlendirildi. "
                f"{row1['product_name']}: kapasite {row1.get('capacity', '-')}, enerji sınıfı {row1.get('energy_class', '-')}, kullanım amacı {row1.get('use_case', '-')}. "
                f"{row2['product_name']}: kapasite {row2.get('capacity', '-')}, enerji sınıfı {row2.get('energy_class', '-')}, kullanım amacı {row2.get('use_case', '-')}. "
                f"Eğer öncelik sadece fiyat ise {cheaper['product_name']} daha ekonomik olabilir; fakat kullanım kolaylığı/uzun vadeli avantajda {winner['product_name']} öne çıkar."
            )

        else:
            score1 = (
                self.feature_score(row1, "usage") * 0.30 +
                self.payment_score(row1, query_info) * 0.25 +
                self.feature_score(row1, "capacity") * 0.20 +
                self.feature_score(row1, "energy") * 0.15 +
                (1 if price1 <= price2 else 0) * 0.10
            )

            score2 = (
                self.feature_score(row2, "usage") * 0.30 +
                self.payment_score(row2, query_info) * 0.25 +
                self.feature_score(row2, "capacity") * 0.20 +
                self.feature_score(row2, "energy") * 0.15 +
                (1 if price2 <= price1 else 0) * 0.10
            )

            winner = row1 if score1 >= score2 else row2

            reason = (
                f"Genel değerlendirmede {winner['product_name']} daha dengeli seçenek görünüyor. "
                f"Fiyat, ödeme seçenekleri, stok, kullanım amacı ve ürün özellikleri birlikte dikkate alındı."
            )

        return winner, reason