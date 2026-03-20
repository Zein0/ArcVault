import json
import re
from openai import OpenAI
from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)


class LLMClient:
    def __init__(self):
        """Initialise the OpenAI-compatible client based on LLM_PROVIDER env var."""
        if LLM_PROVIDER == "ollama":
            self._client = OpenAI(
                base_url=f"{OLLAMA_BASE_URL}/v1",
                api_key="ollama",
            )
            self.model = OLLAMA_MODEL
        else:
            self._client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = OPENAI_MODEL

        self.provider = LLM_PROVIDER

    def chat_json(self, system_prompt: str, user_message: str) -> dict:
        """Send a chat request and return the parsed JSON response."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences before parsing
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
