
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


class OpenAIAdapter:
    def __init__(self):
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is missing")

        self.model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
        self.client = AsyncOpenAI(max_retries=0)

    async def aclose(self):
        await self.client.close()

    async def generate(
        self,
        *,
        instructions: str,
        input_data: dict,
        output_schema: dict,
    ) -> dict:

        response = await self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=json.dumps(input_data, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "agent_output",
                    "strict": True,
                    "schema": output_schema,
                }
            },
            store=False,
        )

        if response.status != "completed":
            raise RuntimeError(
                f"OpenAI response status: {response.status}"
            )

        if not response.output_text:
            raise RuntimeError("OpenAI returned no text")

        payload = json.loads(response.output_text)

        return {
            "payload": payload,
            "provider": "openai",
            "model": self.model,
            "usage": (
                response.usage.model_dump()
                if response.usage
                else None
            ),
        }
