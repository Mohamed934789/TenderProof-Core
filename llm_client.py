"""Provider-neutral interface only. No SDK, keys, prompts or HTTP implementation.
Each member injects an adapter using the existing client argument. Provider/model
configuration stays outside agent logic. No environment names or loader are
implemented here; see README for shared setup and adapter policy.
"""
from typing import Protocol, TypedDict

class LLMResponse(TypedDict):
    payload: dict
    provider: str
    model: str
    usage: dict | None

class LLMClient(Protocol):
    async def generate(
        self, *, instructions: str, input_data: dict, output_schema: dict
    ) -> LLMResponse:
        """Return parsed provider output or raise; never silently retry/fallback.
        Agents must validate payload. Interface conformance does not prove accuracy.
        """
        ...
