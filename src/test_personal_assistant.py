import pandas as pd

from src.personal_shopping_orchestrator import run_personal_shopping_assistant
from src.llm_response_orchestrator import generate_response


def print_case(title, result, answer):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("DECISION:", result.get("decision"))
    print("ANALYSIS:", result.get("analysis_summary"))
    print("\nANSWER:")
    print(answer)

    result_df = result.get("result_df")

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        print("\nPRODUCTS:")
        cols = [
            col for col in [
                "product_name",
                "category",
                "brand",
                "price",
                "stock_status",
                "package_group",
                "rescue_best_price",
                "rescue_best_payment",
            ]
            if col in result_df.columns
        ]

        print(result_df[cols].head(6).to_string(index=False))


def run_tests():
    df = pd.read_csv("data/products.csv")

    test_cases = [
        {
            "title": "1. Kişisel ürün önerisi",
            "query": "Annem için kullanımı kolay telefon öner",
            "mode": "customer",
            "current_results": None,
        },
        {
            "title": "2. Kart limiti yetersiz / sepet kurtarma",
            "query": "Kart limitim yetmedi",
            "mode": "customer",
            "current_results": df[df["category"] == "Telefon"].head(1),
        },
        {
            "title": "3. Çeyiz paketi ve bütçe optimizasyonu",
            "query": "Yeni ev kuruyorum 50000 TL çeyiz paketi yap",
            "mode": "customer",
            "current_results": None,
        },
        {
            "title": "4. Çok pahalı / daha ucuz alternatif",
            "query": "Çok pahalı vazgeçtim",
            "mode": "customer",
            "current_results": df[df["category"] == "Bilgisayar"].head(1),
        },
        {
            "title": "5. Ödeme alternatifi",
            "query": "Senetle buzdolabı alabilir miyim",
            "mode": "customer",
            "current_results": None,
        },
        {
            "title": "6. Mağaza personeli modu",
            "query": "Müşteri kart limitim yetmedi diyor ne önerelim",
            "mode": "store",
            "current_results": df[df["category"] == "Telefon"].head(1),
        },
        {
            "title": "7. Sipariş destek",
            "query": "Siparişim nerede",
            "mode": "customer",
            "current_results": None,
        },
    ]

    for case in test_cases:
        result = run_personal_shopping_assistant(
            products_df=df,
            user_query=case["query"],
            current_results=case["current_results"],
        )

        answer = generate_response(result, case["mode"])

        print_case(
            title=case["title"],
            result=result,
            answer=answer,
        )


if __name__ == "__main__":
    run_tests()