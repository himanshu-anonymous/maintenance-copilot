import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for Google Gemini / Gemma 4 API with persistent HTTP/2 connection,
    SSE streaming, thought-filtering, and latency metrics.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                http2=True,
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _format_model_name(self, model: str) -> str:
        if not model.startswith("models/"):
            return f"models/{model}"
        return model

    async def check_health(self) -> Tuple[bool, str]:
        """Test API connectivity using a minimal ping."""
        if not settings.GEMINI_API_KEY:
            return False, "Missing GEMINI_API_KEY"
        try:
            client = await self.get_client()
            model = self._format_model_name(settings.LLM_MODEL)
            url = f"{self.base_url}/{model}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": "Ping"}]}],
                "generationConfig": {"maxOutputTokens": 5}
            }
            resp = await client.post(url, json=payload, timeout=6.0)
            if resp.status_code == 200:
                return True, "healthy"
            return False, f"HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            return False, str(e)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        response_json: bool = False
    ) -> Dict[str, Any]:
        """Non-streaming generation returning response text and execution latency."""
        client = await self.get_client()
        target_model = self._format_model_name(model or settings.LLM_MODEL)
        url = f"{self.base_url}/{target_model}:generateContent?key={settings.GEMINI_API_KEY}"

        combined_text = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}" if system_instruction else prompt
        contents = [{"parts": [{"text": combined_text}]}]

        gen_config: Dict[str, Any] = {
            "maxOutputTokens": max_tokens,
        }
        if response_json:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": contents,
            "generationConfig": gen_config
        }

        t0 = time.perf_counter()
        resp = await client.post(url, json=payload, timeout=12.0)
        total_time_ms = int((time.perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Gemini API returned status {resp.status_code}: {resp.text[:200]}",
                request=resp.request,
                response=resp
            )

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return {"text": "", "total_ms": total_time_ms, "model": target_model}

        parts = candidates[0].get("content", {}).get("parts", [])
        user_facing_text = ""
        for p in parts:
            if not p.get("thought", False):
                user_facing_text += p.get("text", "")

        return {
            "text": user_facing_text.strip(),
            "total_ms": total_time_ms,
            "model": target_model
        }

    async def stream_generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming generation using SSE endpoint.
        Filters out 'thought: True' parts.
        Yields dicts with:
        {'type': 'chunk', 'text': chunk, 'first_token_ms': int, 'total_ms': int}
        or {'type': 'done', 'total_ms': int}
        """
        client = await self.get_client()
        target_model = self._format_model_name(model or settings.LLM_MODEL)
        url = f"{self.base_url}/{target_model}:streamGenerateContent?key={settings.GEMINI_API_KEY}&alt=sse"

        combined_text = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}" if system_instruction else prompt
        contents = [{"parts": [{"text": combined_text}]}]

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
            }
        }

        t0 = time.perf_counter()
        first_token_time: Optional[int] = None

        try:
            async with client.stream("POST", url, json=payload, timeout=httpx.Timeout(15.0, connect=5.0)) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    raise httpx.HTTPStatusError(
                        f"Stream API returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')[:200]}",
                        request=resp.request,
                        response=resp
                    )

                buffer = ""
                async for raw_chunk in resp.aiter_text():
                    buffer += raw_chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line.startswith("data: "):
                            continue
                        json_str = line[6:].strip()
                        if not json_str:
                            continue
                        try:
                            chunk_data = json.loads(json_str)
                            candidates = chunk_data.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                now = int((time.perf_counter() - t0) * 1000)
                                # Filter out model internal thoughts from user-facing stream
                                if p.get("thought", False):
                                    yield {
                                        "type": "thinking",
                                        "elapsed_ms": now
                                    }
                                    continue

                                text_piece = p.get("text", "")
                                if text_piece:
                                    if first_token_time is None:
                                        first_token_time = now
                                    yield {
                                        "type": "chunk",
                                        "text": text_piece,
                                        "first_token_ms": first_token_time,
                                        "elapsed_ms": now,
                                    }
                        except json.JSONDecodeError:
                            continue

            total_ms = int((time.perf_counter() - t0) * 1000)
            yield {
                "type": "done",
                "first_token_ms": first_token_time or total_ms,
                "total_ms": total_ms,
                "model": target_model,
            }

        except Exception as e:
            logger.warning(f"SSE stream failed on {target_model} ({e}). Falling back to non-streaming generateContent.")
            try:
                # Resilient fallback: call generateContent and stream the tokens smoothly
                res = await self.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    model=target_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                generated_text = res.get("text", "")
                words = generated_text.split(" ")
                now = int((time.perf_counter() - t0) * 1000)
                first_token_time = now

                # Yield words in realistic small streaming bursts
                chunk_buffer = []
                for idx, w in enumerate(words):
                    chunk_buffer.append(w)
                    if len(chunk_buffer) >= 4 or idx == len(words) - 1:
                        yield {
                            "type": "chunk",
                            "text": " ".join(chunk_buffer) + " ",
                            "first_token_ms": first_token_time,
                            "elapsed_ms": int((time.perf_counter() - t0) * 1000)
                        }
                        chunk_buffer = []
                        await asyncio.sleep(0.01)

                total_ms = int((time.perf_counter() - t0) * 1000)
                yield {
                    "type": "done",
                    "first_token_ms": first_token_time,
                    "total_ms": total_ms,
                    "model": target_model,
                }
            except Exception as non_stream_exc:
                yield {
                    "type": "error",
                    "error": str(non_stream_exc),
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                }


gemini_client = GeminiClient()
