import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from app.config import settings
from app.llm.gemini import gemini_client

logger = logging.getLogger(__name__)


async def stream_with_fallback(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 600,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streams from primary model (LLM_MODEL).
    If no first token arrives within FIRST_TOKEN_TIMEOUT_MS, or an HTTP error/500 occurs,
    automatically cancels and switches to LLM_FALLBACK_MODEL, and then to high-speed gemini-3-flash-preview.
    """
    first_token_timeout_sec = settings.FIRST_TOKEN_TIMEOUT_MS / 1000.0
    models_to_try = [
        settings.LLM_MODEL,
        settings.LLM_FALLBACK_MODEL,
        "models/gemini-3-flash-preview"
    ]
    seen = set()
    candidate_models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            candidate_models.append(m)

    for idx, target_model in enumerate(candidate_models):
        first_token_received = False
        failed = False

        try:
            stream_iter = gemini_client.stream_generate(
                prompt=prompt,
                system_instruction=system_instruction,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            while True:
                try:
                    timeout = None if first_token_received else first_token_timeout_sec
                    chunk = await asyncio.wait_for(stream_iter.__anext__(), timeout=timeout)

                    if chunk.get("type") == "error":
                        logger.warning(f"Error on model {target_model}: {chunk.get('error')}")
                        failed = True
                        break

                    if chunk.get("type") in ("chunk", "thinking"):
                        first_token_received = True

                    if chunk.get("type") != "thinking":
                        yield chunk

                    if chunk.get("type") == "done":
                        return

                except asyncio.TimeoutError:
                    logger.warning(f"First token timeout ({settings.FIRST_TOKEN_TIMEOUT_MS}ms) on {target_model}.")
                    failed = True
                    break
                except StopAsyncIteration:
                    return

        except Exception as exc:
            logger.warning(f"Exception during stream on {target_model}: {exc}")
            failed = True

        if not failed and first_token_received:
            return

        if idx == len(candidate_models) - 1:
            yield {
                "type": "error",
                "error": "All LLM models in fallback chain exhausted."
            }
