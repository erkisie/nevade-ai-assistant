import io
import contextlib
import warnings


# =====================================================
# LLM PROVIDER ROUTER
# Öncelik:
# 1. Ollama
# 2. Gemini
# 3. Fallback
# =====================================================


def call_gemini_safely(prompt):
    """
    Gemini sadece gerektiğinde import edilir.
    Quota / deprecated warning / traceback sistemi bozmaz.
    """

    try:
        fake_stdout = io.StringIO()
        fake_stderr = io.StringIO()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            with contextlib.redirect_stdout(fake_stdout), contextlib.redirect_stderr(fake_stderr):
                try:
                    from llm_service import call_gemini
                except Exception:
                    return None

                answer = call_gemini(prompt)

        if answer and str(answer).strip():
            return str(answer).strip()

    except Exception:
        return None

    return None


def call_ollama_safely(prompt, model_name="llama3.2:1b"):
    """
    Ollama kuruluysa lokal LLM kullanır.
    Hata olursa sessizce None döner.
    Küçük model için düşük temperature kullanılır.
    """

    try:
        import requests

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "num_predict": 350,
                },
            },
            timeout=60,
        )

        if response.status_code != 200:
            return None

        data = response.json()
        answer = data.get("response", "")

        if answer and str(answer).strip():
            return str(answer).strip()

    except Exception:
        return None

    return None

def call_best_available_llm(prompt):
    """
    En iyi uygun LLM'i seçer.
    Hata olursa sistem fallback cevaba döner.
    """

    ollama_answer = call_ollama_safely(prompt)

    if ollama_answer:
        return {
            "provider": "Ollama",
            "answer": ollama_answer,
        }

    gemini_answer = call_gemini_safely(prompt)

    if gemini_answer:
        return {
            "provider": "Gemini",
            "answer": gemini_answer,
        }

    return {
        "provider": "Fallback",
        "answer": None,
    }