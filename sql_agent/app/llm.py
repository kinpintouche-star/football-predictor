import inspect
import os


def ask_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    from litai import LLM

    api_key = os.getenv("LIGHTNING_API_KEY")
    model = model or os.getenv("LLM_MODEL", "openai/gpt-5.4-mini-2026-03-17")
    max_tokens = max_tokens or int(os.getenv("LLM_MAX_RESPONSE_TOKENS", "1600"))

    if not api_key:
        raise RuntimeError("LIGHTNING_API_KEY est requis")

    prompt = f"""
{system_prompt}

Question utilisateur :
{user_prompt}
"""

    llm = LLM(model=model, api_key=api_key)
    chat_kwargs = {}
    chat_params = inspect.signature(llm.chat).parameters
    accepts_kwargs = any(param.kind == param.VAR_KEYWORD for param in chat_params.values())

    if "max_tokens" in chat_params:
        chat_kwargs["max_tokens"] = max_tokens
    elif "max_output_tokens" in chat_params:
        chat_kwargs["max_output_tokens"] = max_tokens
    elif "max_new_tokens" in chat_params:
        chat_kwargs["max_new_tokens"] = max_tokens
    elif accepts_kwargs:
        chat_kwargs["max_tokens"] = max_tokens

    try:
        return str(llm.chat(prompt, **chat_kwargs))
    except TypeError:
        return str(llm.chat(prompt))
