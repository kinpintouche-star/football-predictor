import os


def ask_llm(system_prompt: str, user_prompt: str) -> str:
    from litai import LLM

    api_key = os.getenv("LIGHTNING_API_KEY")
    model = os.getenv("LLM_MODEL", "openai/gpt-5.4-mini-2026-03-17")

    if not api_key:
        raise RuntimeError("LIGHTNING_API_KEY est requis")

    prompt = f"""
{system_prompt}

Question utilisateur :
{user_prompt}
"""

    llm = LLM(model=model, api_key=api_key)
    return str(llm.chat(prompt))
