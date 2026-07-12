from typing import Any

import anthropic


class AnthropicAdapter:
    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        tools: list[dict],
    ) -> anthropic.types.Message:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        return await self._client.messages.create(**kwargs)
