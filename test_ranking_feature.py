import pandas as pd

from src.personal_shopping_orchestrator import run_personal_shopping_assistant
from src.llm_response_orchestrator import generate_response


def run_test():
    df = pd.read_csv("data/products.csv")

    context = {}

    r1 = run_personal_shopping_assistant(
        products_df=df,
        user_query="Telefon öner",
        customer_context=context,
    )

    context["customer_profile"] = r1.get("customer_profile")

    print("\n--- İLK ÖNERİ ---")
    print("DECISION:", r1.get("decision"))
    print(generate_response(r1, "customer"))

    r2 = run_personal_shopping_assistant(
        products_df=df,
        user_query="En düşük aylık ödemeye göre sırala",
        current_results=r1.get("result_df"),
        customer_context=context,
    )

    context["customer_profile"] = r2.get("customer_profile")

    print("\n--- YENİDEN SIRALAMA ---")
    print("DECISION:", r2.get("decision"))
    print("STRATEGY:", r2.get("ranking_strategy"))
    print(generate_response(r2, "customer"))


if __name__ == "__main__":
    run_test()