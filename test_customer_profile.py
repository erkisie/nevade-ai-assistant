import pandas as pd

from src.personal_shopping_orchestrator import run_personal_shopping_assistant
from src.llm_response_orchestrator import generate_response


def run_profile_test():
    df = pd.read_csv("data/products.csv")

    customer_context = {}

    print("\n--- 1. MESAJ ---")
    r1 = run_personal_shopping_assistant(
        products_df=df,
        user_query="Annem için kullanımı kolay telefon öner",
        customer_context=customer_context,
    )

    customer_context["customer_profile"] = r1.get("customer_profile")

    print("DECISION:", r1.get("decision"))
    print("ANALYSIS:", r1.get("analysis_summary"))
    print("PROFILE:", r1.get("profile_summary"))
    print(generate_response(r1, "customer"))

    print("\n--- 2. MESAJ / FOLLOW-UP ---")
    r2 = run_personal_shopping_assistant(
        products_df=df,
        user_query="Daha ucuzu var mı?",
        current_results=r1.get("result_df"),
        customer_context=customer_context,
    )

    customer_context["customer_profile"] = r2.get("customer_profile")

    print("DECISION:", r2.get("decision"))
    print("ANALYSIS:", r2.get("analysis_summary"))
    print("PROFILE:", r2.get("profile_summary"))
    print(generate_response(r2, "customer"))

    print("\n--- 3. MESAJ / ÖDEME FOLLOW-UP ---")
    r3 = run_personal_shopping_assistant(
        products_df=df,
        user_query="Senet olur mu?",
        current_results=r2.get("result_df"),
        customer_context=customer_context,
    )

    customer_context["customer_profile"] = r3.get("customer_profile")

    print("DECISION:", r3.get("decision"))
    print("ANALYSIS:", r3.get("analysis_summary"))
    print("PROFILE:", r3.get("profile_summary"))
    print(generate_response(r3, "customer"))


if __name__ == "__main__":
    run_profile_test()