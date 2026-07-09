import re
import math
import pandas as pd
from collections import Counter, defaultdict


# =====================================================
# SEMANTIC ENGINE
# Amaç:
# Kullanıcı kelimeyi birebir yazmasa bile doğru ürünleri bulmak.
# Örn:
# "balkonda içecek saklamak için küçük bir şey"
# -> mini buzdolabı / buzdolabı
# =====================================================


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


def tokenize(text):
    text = normalize_text(text)

    stopwords = {
        "bir", "ve", "veya", "icin", "gibi", "olan", "olsun",
        "var", "mi", "ne", "en", "daha", "bana", "lazim",
        "istiyorum", "oner", "onerir", "olur", "mu", "de",
        "da", "bu", "su", "o", "ben", "ile", "ama", "cok",
        "az", "biraz", "icin", "şey", "sey",
    }

    tokens = []

    for token in text.split():
        if len(token) <= 2:
            continue

        if token in stopwords:
            continue

        tokens.append(token)

    return tokens


# =====================================================
# KAVRAM GENİŞLETME
# =====================================================

CONCEPT_EXPANSIONS = {
    "mini_buzdolabi": [
        "mini buzdolabi",
        "minibar",
        "mini bar",
        "kucuk buzdolabi",
        "sogutucu",
        "icecek sogutucu",
        "soguk icecek saklama",
        "az yer kaplayan buzdolabi",
        "balkon icin sogutucu",
        "ofis icin mini buzdolabi",
        "kompakt buzdolabi",
    ],
    "buzdolabi": [
        "buzdolabi",
        "no frost",
        "sogutma",
        "yiyecek saklama",
        "icecek saklama",
        "mutfak",
        "genis hacim",
        "derin dondurucu",
        "beyaz esya",
    ],
    "ogrenci_laptop": [
        "ogrenci laptop",
        "ders",
        "odev",
        "sunum",
        "universite",
        "ofis programlari",
        "hafif laptop",
        "fiyat performans bilgisayar",
        "gunluk kullanim bilgisayar",
        "notebook",
    ],
    "gaming_laptop": [
        "oyun bilgisayari",
        "gaming laptop",
        "ekran karti",
        "performans",
        "oyun",
        "yuksek islemci",
    ],
    "telefon_gunluk": [
        "telefon",
        "sosyal medya",
        "kamera",
        "batarya",
        "gunluk kullanim",
        "akilli telefon",
        "android",
        "iphone",
        "galaxy",
    ],
    "televizyon_salon": [
        "televizyon",
        "tv",
        "smart tv",
        "akilli tv",
        "salon",
        "film",
        "dizi",
        "4k",
        "genis ekran",
        "netflix",
    ],
    "camasir_makinesi": [
        "camasir makinesi",
        "yikama",
        "kg kapasite",
        "gunluk camasir",
        "enerji verimli",
        "beyaz esya",
    ],
    "bulasik_makinesi": [
        "bulasik makinesi",
        "bulasik",
        "mutfak",
        "programli",
        "beyaz esya",
    ],
    "supurge": [
        "supurge",
        "temizlik",
        "ev temizligi",
        "toz alma",
        "robot supurge",
        "dikey supurge",
        "elektrikli supurge",
    ],
    "ceyiz_paketi": [
        "ceyiz",
        "evleniyorum",
        "dugun",
        "ev kuruyorum",
        "ev diziyorum",
        "paket",
        "beyaz esya",
        "televizyon",
        "supurge",
        "camasir",
        "buzdolabi",
        "bulasik",
    ],
}


QUERY_RULES = [
    {
        "triggers": [
            "soguk icecek",
            "icecek sakla",
            "icecek saklamak",
            "balkon",
            "az yer",
            "kucuk",
            "mini",
            "yer kaplamayan",
            "sogutucu",
            "minibar",
        ],
        "concepts": ["mini_buzdolabi", "buzdolabi"],
    },
    {
        "triggers": ["buzdolabi", "buz dolabi", "no frost", "mutfak", "sogutma"],
        "concepts": ["buzdolabi"],
    },
    {
        "triggers": ["ogrenci", "ders", "odev", "universite", "sunum", "okul"],
        "concepts": ["ogrenci_laptop"],
    },
    {
        "triggers": ["oyun", "gaming", "performans", "ekran karti"],
        "concepts": ["gaming_laptop"],
    },
    {
        "triggers": ["sosyal medya", "kamera", "batarya", "gunluk telefon"],
        "concepts": ["telefon_gunluk"],
    },
    {
        "triggers": ["salon", "film", "dizi", "netflix", "genis ekran"],
        "concepts": ["televizyon_salon"],
    },
    {
        "triggers": ["evleniyorum", "ceyiz", "dugun", "ev kuruyorum", "ev diziyorum", "paket"],
        "concepts": ["ceyiz_paketi"],
    },
    {
        "triggers": ["temizlik", "ev temizligi", "toz", "supurmek"],
        "concepts": ["supurge"],
    },
]


def expand_query_with_concepts(user_query):
    q = normalize_text(user_query)
    additions = []

    for rule in QUERY_RULES:
        if any(trigger in q for trigger in rule["triggers"]):
            for concept in rule["concepts"]:
                additions.extend(CONCEPT_EXPANSIONS.get(concept, []))

    expanded = q + " " + " ".join(additions)
    return normalize_text(expanded)


def row_to_semantic_text(row):
    fields = [
        "product_name",
        "category",
        "brand",
        "description",
        "features",
        "use_case",
        "payment_options",
        "stock_status",
    ]

    parts = []

    for field in fields:
        try:
            value = row.get(field, "")
        except Exception:
            value = ""

        if value is not None:
            parts.append(str(value))

    base_text = normalize_text(" ".join(parts))
    expanded_parts = [base_text]

    if "buzdolabi" in base_text or "no frost" in base_text or "minibar" in base_text or "sogutucu" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["buzdolabi"])

    if "mini" in base_text and ("buzdolabi" in base_text or "sogutucu" in base_text or "bar" in base_text):
        expanded_parts.extend(CONCEPT_EXPANSIONS["mini_buzdolabi"])

    if "laptop" in base_text or "bilgisayar" in base_text or "notebook" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["ogrenci_laptop"])

    if "gaming" in base_text or "oyun" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["gaming_laptop"])

    if "telefon" in base_text or "iphone" in base_text or "galaxy" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["telefon_gunluk"])

    if "televizyon" in base_text or "smart tv" in base_text or re.search(r"\btv\b", base_text):
        expanded_parts.extend(CONCEPT_EXPANSIONS["televizyon_salon"])

    if "camasir" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["camasir_makinesi"])

    if "bulasik" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["bulasik_makinesi"])

    if "supurge" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["supurge"])

    if "ceyiz" in base_text:
        expanded_parts.extend(CONCEPT_EXPANSIONS["ceyiz_paketi"])

    return normalize_text(" ".join(expanded_parts))


# =====================================================
# TF-IDF / COSINE
# =====================================================

def build_tfidf_vectors(documents):
    tokenized_docs = [tokenize(doc) for doc in documents]

    doc_count = len(tokenized_docs)
    document_frequency = defaultdict(int)

    for tokens in tokenized_docs:
        for token in set(tokens):
            document_frequency[token] += 1

    vectors = []

    for tokens in tokenized_docs:
        token_counts = Counter(tokens)
        total_tokens = max(1, len(tokens))
        vector = {}

        for token, count in token_counts.items():
            tf = count / total_tokens
            idf = math.log((doc_count + 1) / (document_frequency[token] + 1)) + 1
            vector[token] = tf * idf

        vectors.append(vector)

    return vectors


def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0

    common_tokens = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[token] * vec2[token] for token in common_tokens)

    norm1 = math.sqrt(sum(value * value for value in vec1.values()))
    norm2 = math.sqrt(sum(value * value for value in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return numerator / (norm1 * norm2)


def semantic_scores(products_df, user_query):
    if products_df is None or products_df.empty:
        return []

    query_text = expand_query_with_concepts(user_query)
    product_texts = [row_to_semantic_text(row) for _, row in products_df.iterrows()]

    all_documents = [query_text] + product_texts
    vectors = build_tfidf_vectors(all_documents)

    query_vector = vectors[0]
    product_vectors = vectors[1:]

    scores = []

    for vector in product_vectors:
        score = cosine_similarity(query_vector, vector)
        scores.append(score)

    return scores


# =====================================================
# APP İÇİN GEREKEN ANA FONKSİYONLAR
# =====================================================

def semantic_candidate_search(products_df, user_query, top_k=12, min_score=0.01):
    """
    Karar motorundan önce semantic aday havuzu oluşturur.
    Strict filter sonrası kalan ürünler içinde anlamsal benzerliğe göre sıralama yapar.
    """

    if products_df is None or products_df.empty:
        return products_df

    df = products_df.copy()
    scores = semantic_scores(df, user_query)

    if not scores:
        df["semantic_score"] = 0
        return df.head(top_k)

    df["semantic_score"] = scores
    df = df.sort_values("semantic_score", ascending=False)

    if "semantic_score" in df.columns and df["semantic_score"].max() > min_score:
        df = df[df["semantic_score"] >= min_score]

    return df.head(top_k)


def apply_semantic_reranking(result_df, user_query):
    """
    Karar motorundan sonra gelen ürünleri semantic skora göre yeniden sıralar.
    """

    if result_df is None or result_df.empty:
        return result_df

    df = result_df.copy()
    scores = semantic_scores(df, user_query)

    if not scores:
        return df

    df["semantic_score"] = scores

    if "score" in df.columns:
        df["final_ai_score"] = df["score"].apply(safe_number) + (df["semantic_score"] * 100)
    else:
        df["final_ai_score"] = df["semantic_score"] * 100

    df = df.sort_values("final_ai_score", ascending=False)

    return df


def explain_semantic_match(row, user_query):
    query_expanded = expand_query_with_concepts(user_query)
    row_text = row_to_semantic_text(row)

    query_tokens = set(tokenize(query_expanded))
    row_tokens = set(tokenize(row_text))

    common = list(query_tokens & row_tokens)
    common = common[:8]

    if not common:
        return "Anlamsal benzerlik ürün açıklaması ve kullanım amacı üzerinden hesaplandı."

    return "Eşleşen anlam sinyalleri: " + ", ".join(common)


# Eski app sürümleri farklı isim beklerse bozulmasın diye alias
def semantic_search_products(products_df, user_query, top_k=12, min_score=0.01):
    return semantic_candidate_search(products_df, user_query, top_k=top_k, min_score=min_score)


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    test_products = pd.DataFrame(
        [
            {
                "product_name": "Beko No Frost Buzdolabı 500 L",
                "category": "Beyaz Eşya",
                "brand": "Beko",
                "description": "Geniş hacimli No Frost buzdolabı",
                "features": "No Frost, sessiz çalışma",
                "use_case": "Çeyiz ve ev kullanımı",
                "payment_options": "Senet, havale, kredi kartı",
                "stock_status": "Stokta",
            },
            {
                "product_name": "Vestel Mini Bar Buzdolabı 90 L",
                "category": "Beyaz Eşya",
                "brand": "Vestel",
                "description": "Az yer kaplayan mini buzdolabı ve içecek soğutucu",
                "features": "Kompakt tasarım, düşük ses",
                "use_case": "Balkon, ofis, küçük oda, içecek saklama",
                "payment_options": "Kart, havale",
                "stock_status": "Stokta",
            },
            {
                "product_name": "Asus Vivobook 15 Laptop",
                "category": "Bilgisayar",
                "brand": "Asus",
                "description": "Öğrenci ve temel ofis işleri için laptop",
                "features": "16 GB RAM, SSD",
                "use_case": "Öğrenci, ofis, ders, sunum",
                "payment_options": "Kart, taksit, senet",
                "stock_status": "Stokta",
            },
            {
                "product_name": "Samsung 50 inç Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "description": "Salon için akıllı televizyon",
                "features": "4K Smart TV",
                "use_case": "Salon, film, dizi",
                "payment_options": "Kart, taksit, senet",
                "stock_status": "Stokta",
            },
        ]
    )

    test_queries = [
        "Yazın balkonda soğuk içeceklerimi saklayacağım küçük bir şey lazım",
        "Öğrenci için ders ve sunum yapmalık bilgisayar var mı?",
        "Salonda film izlemek için geniş ekran bir şey arıyorum",
        "Ev temizliği için pratik bir şey lazım",
    ]

    for query in test_queries:
        print("\nSORU:", query)
        result = semantic_candidate_search(test_products, query)
        print(result[["product_name", "semantic_score"]])