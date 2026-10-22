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
    max_tokens: int = 1200,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streams from primary model (LLM_MODEL).
    If no first token arrives within FIRST_TOKEN_TIMEOUT_MS, or an error occurs,
    automatically cancels and switches to LLM_FALLBACK_MODEL.
    """
    first_token_timeout_sec = settings.FIRST_TOKEN_TIMEOUT_MS / 1000.0
    primary_model = settings.LLM_MODEL
    fallback_model = settings.LLM_FALLBACK_MODEL

    first_token_received = False
    use_fallback = False

    async def _run_stream(target_model: str):
        async for item in gemini_client.stream_generate(
            prompt=prompt,
            system_instruction=system_instruction,
            model=target_model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield item

    stream_iter = _run_stream(primary_model)

    try:
        while True:
            try:
                # Wait for next chunk, enforcing first token timeout if not received yet
                timeout = None if first_token_received else first_token_timeout_sec
                chunk = await asyncio.wait_for(stream_iter.__anext__(), timeout=timeout)

                if chunk.get("type") == "error":
                    logger.warning(f"Error on primary model {primary_model}: {chunk.get('error')}. Falling back.")
                    use_fallback = True
                    break

                if chunk.get("type") == "chunk":
                    first_token_received = True

                yield chunk

                if chunk.get("type") == "done":
                    return

            except asyncio.TimeoutError:
                logger.warning(f"First token timeout ({settings.FIRST_TOKEN_TIMEOUT_MS}ms) on {primary_model}. Falling back to {fallback_model}.")
                use_fallback = True
                break
            except StopAsyncIteration:
                return

    except Exception as exc:
        logger.warning(f"Exception during stream on {primary_model}: {exc}. Falling back.")
        use_fallback = True

    if use_fallback:
        logger.info(f"Executing fallback stream with {fallback_model}")
        try:
            async for chunk in _run_stream(fallback_model):
                yield chunk
        except Exception as fallback_exc:
            logger.error(f"Fallback model failed as well: {fallback_exc}")
            yield {
                "type": "error",
                "error": f"LLM generation failed: {str(fallback_exc)}"
            }
