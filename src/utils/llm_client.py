"""
LLM API Client - Supports GLM, Claude, and OpenAI
For use with Recursive Language Model implementation
"""

import os
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None


class LLMClient:
    """
    Universal LLM client supporting multiple providers:
    - GLM (Zhipu AI)
    - Claude (Anthropic)
    - OpenAI (GPT)
    """

    def __init__(self,
                 provider: str = "glm",
                 api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """
        Initialize LLM client

        Args:
            provider: "glm", "claude", or "openai"
            api_key: API key (will read from env if not provided)
            model: Model name (uses default if not provided)
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_default_model()

        if self.provider == "claude" and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def _get_api_key(self) -> str:
        """Get API key from environment"""
        key_map = {
            "glm": "GLM_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
        env_key = key_map.get(self.provider, "GLM_API_KEY")
        key = os.getenv(env_key)
        if not key:
            raise ValueError(f"API key not found. Set {env_key} environment variable.")
        return key

    def _get_default_model(self) -> str:
        """Get default model for provider"""
        model_map = {
            "glm": "glm-4-plus",
            "claude": "claude-sonnet-4-5-20251101",
            "openai": "gpt-4o"
        }
        return model_map.get(self.provider, "glm-4-plus")

    def chat(self,
             messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 4096,
             **kwargs) -> LLMResponse:
        """
        Send chat completion request

        Args:
            messages: List of {role, content} messages
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            **kwargs: Additional provider-specific params

        Returns:
            LLMResponse with content and metadata
        """
        if self.provider == "glm":
            return self._glm_chat(messages, temperature, max_tokens, **kwargs)
        elif self.provider == "claude":
            return self._claude_chat(messages, temperature, max_tokens, **kwargs)
        elif self.provider == "openai":
            return self._openai_chat(messages, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _glm_chat(self,
                  messages: List[Dict[str, str]],
                  temperature: float,
                  max_tokens: int,
                  **kwargs) -> LLMResponse:
        """GLM API chat completion"""
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            cost_estimate=self._estimate_glm_cost(tokens)
        )

    def _claude_chat(self,
                     messages: List[Dict[str, str]],
                     temperature: float,
                     max_tokens: int,
                     **kwargs) -> LLMResponse:
        """Claude API chat completion"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required for Claude. Install: pip install anthropic")

        # Convert messages format for Claude
        # Claude API expects system message separate
        system_msg = None
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        response = self.client.messages.create(
            model=self.model,
            system=system_msg,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            cost_estimate=self._estimate_claude_cost(tokens)
        )

    def _openai_chat(self,
                      messages: List[Dict[str, str]],
                      temperature: float,
                      max_tokens: int,
                      **kwargs) -> LLMResponse:
        """OpenAI API chat completion"""
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            cost_estimate=self._estimate_openai_cost(tokens)
        )

    def _estimate_glm_cost(self, tokens: Optional[int]) -> Optional[float]:
        """Estimate GLM API cost (rough estimate)"""
        if tokens is None:
            return None
        # GLM-4-plus: ~$0.50 per 1M tokens (estimate)
        return (tokens / 1_000_000) * 0.50

    def _estimate_claude_cost(self, tokens: Optional[int]) -> Optional[float]:
        """Estimate Claude API cost"""
        if tokens is None:
            return None
        # Claude Sonnet 4.5: $3 per 1M input, $15 per 1M output
        # Assume 50/50 split for estimation
        return (tokens / 2 / 1_000_000) * 3 + (tokens / 2 / 1_000_000) * 15

    def _estimate_openai_cost(self, tokens: Optional[int]) -> Optional[float]:
        """Estimate OpenAI API cost"""
        if tokens is None:
            return None
        # GPT-4o: $2.50 per 1M input, $10 per 1M output
        return (tokens / 2 / 1_000_000) * 2.50 + (tokens / 2 / 1_000_000) * 10

    def analyze_json(self,
                     data: Any,
                     task: str,
                     context: str = "",
                     temperature: float = 0.7) -> str:
        """
        Convenience method for analyzing JSON data

        Args:
            data: Python data structure (will be JSON serialized)
            task: Analysis task description
            context: Additional context
            temperature: Sampling temperature

        Returns:
            Analysis text
        """
        # Limit data size for single request
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        # If too large, truncate with warning
        if len(json_str) > 50000:
            json_str = json_str[:50000] + "\n... [TRUNCATED]"

        prompt = f"""
{context}

Task: {task}

Data to analyze:
```json
{json_str}
```

Provide analysis focusing on the task above.
"""

        response = self.chat([{"role": "user", "content": prompt}], temperature)
        return response.content


def create_llm_client(provider: str = "glm") -> LLMClient:
    """
    Factory function to create LLM client

    Args:
        provider: "glm", "claude", or "openai"

    Returns:
        Configured LLMClient instance
    """
    return LLMClient(provider=provider)
