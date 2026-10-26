"""Adapter and strict-schema acceptance checks, entirely offline."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agent1 import eligibility_output_schema
from agent2_schema import agent2_output_schema
from agent3 import verification_output_schema
from openai_adapter import OpenAIAdapter


@pytest.mark.parametrize("schema", [eligibility_output_schema(), agent2_output_schema(), verification_output_schema()])
def test_schemas_have_strict_object_definitions(schema):
    def check(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
            for child in node["properties"].values():
                check(child)
        elif node.get("type") == "array":
            check(node["items"])
    assert schema["type"] == "object"
    check(schema)


@pytest.mark.asyncio
async def test_adapter_passes_schema_and_parses_json_without_network():
    adapter = OpenAIAdapter.__new__(OpenAIAdapter)
    adapter.model = "offline-test"
    response = SimpleNamespace(status="completed", output_text='{"requirements": [], "warnings": []}', usage=None)
    create = AsyncMock(return_value=response)
    adapter.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    schema = eligibility_output_schema()
    output = await adapter.generate(instructions="test", input_data={"text": "عربي"}, output_schema=schema)
    assert output["payload"] == {"requirements": [], "warnings": []}
    request = create.call_args.kwargs
    assert request["store"] is False
    assert request["text"]["format"] == {"type": "json_schema", "name": "agent_output", "strict": True, "schema": schema}
    assert json.loads(request["input"]) == {"text": "عربي"}
    assert create.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status,text", [("incomplete", "{}"), ("completed", ""), ("completed", "bad-json")])
async def test_adapter_failure_does_not_retry_or_fallback(status, text):
    adapter = OpenAIAdapter.__new__(OpenAIAdapter)
    adapter.model = "offline-test"
    create = AsyncMock(return_value=SimpleNamespace(status=status, output_text=text, usage=None))
    adapter.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    with pytest.raises((RuntimeError, ValueError)):
        await adapter.generate(instructions="test", input_data={}, output_schema=eligibility_output_schema())
    assert create.await_count == 1


def test_adapter_disables_sdk_retries():
    with patch("openai_adapter.load_dotenv"), patch("openai_adapter.os.getenv", return_value="offline-test"), patch("openai_adapter.AsyncOpenAI") as sdk:
        OpenAIAdapter()
    sdk.assert_called_once_with(max_retries=0)
