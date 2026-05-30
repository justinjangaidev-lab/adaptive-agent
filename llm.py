import httpx


class LLMClient:
    """OpenAI 호환 또는 Anthropic LLM 엔드포인트에 직접 HTTP 호출. SDK 미사용.
    Direct HTTP calls to an OpenAI-compatible or Anthropic LLM endpoint. No SDK used."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        max_tokens: int = 4096,
        provider: str = "openai",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.provider = provider

    def chat(self, messages: list[dict], system: str) -> str:
        """대화 메시지를 LLM에 전송하고 응답 텍스트를 반환한다.
        Send conversation messages to the LLM and return the raw text response."""
        if self.provider == "anthropic":
            return self._chat_anthropic(messages, system)
        return self._chat_openai(messages, system)

    def _chat_openai(self, messages: list[dict], system: str) -> str:
        """OpenAI 호환 엔드포인트용 요청 형식 (OpenRouter, Ollama 포함).
        Request format for OpenAI-compatible endpoints (including OpenRouter, Ollama)."""
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system}] + messages,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(self.base_url, headers=headers, json=body, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""

    def _chat_anthropic(self, messages: list[dict], system: str) -> str:
        """Anthropic 네이티브 API 요청 형식 (system을 최상위 필드로 분리).
        Request format for Anthropic native API (system as a top-level field)."""
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        resp = httpx.post(self.base_url, headers=headers, json=body, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"] or ""
