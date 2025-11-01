# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""LangChain-based LLM client wrapper."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import Ollama

from ant_agent.utils.config import LLMProvider, ModelConfig


class LLMClient:
    """LangChain-based LLM client supporting multiple providers."""

    def __init__(self, model_config: ModelConfig):
        """Initialize LLM client with model configuration."""
        self.model_config = model_config
        self.provider = model_config.model_provider
        self._client = self._create_client()

    def _create_client(self) -> BaseLanguageModel:
        """Create LangChain client based on provider."""
        common_params = {
            "model": self.model_config.model,
            "temperature": self.model_config.temperature,
            "max_tokens": self.model_config.max_tokens,
            "max_retries": self.model_config.max_retries,
        }

        if self.model_config.api_key:
            common_params["api_key"] = self.model_config.api_key
        elif hasattr(self, '_get_api_key_from_env'):
            common_params["api_key"] = self._get_api_key_from_env()

        if self.model_config.base_url:
            common_params["base_url"] = self.model_config.base_url

        match self.provider:
            case LLMProvider.OPENAI:
                return ChatOpenAI(**common_params)

            case LLMProvider.ANTHROPIC:
                # Anthropic uses different parameter names
                anthropic_params = {
                    "model": self.model_config.model,
                    "temperature": self.model_config.temperature,
                    "max_tokens": self.model_config.max_tokens,
                    "max_retries": self.model_config.max_retries,
                }
                if self.model_config.api_key:
                    anthropic_params["api_key"] = self.model_config.api_key
                if self.model_config.base_url:
                    anthropic_params["base_url"] = self.model_config.base_url
                return ChatAnthropic(**anthropic_params)

            case LLMProvider.GOOGLE:
                return ChatGoogleGenerativeAI(**common_params)

            case LLMProvider.OLLAMA:
                # Ollama uses different parameters
                ollama_params = {
                    "model": self.model_config.model,
                    "temperature": self.model_config.temperature,
                }
                if self.model_config.base_url:
                    ollama_params["base_url"] = self.model_config.base_url
                return Ollama(**ollama_params)

            case LLMProvider.OPENROUTER:
                # OpenRouter uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://openrouter.ai/api/v1"
                return ChatOpenAI(**common_params)

            case LLMProvider.DEEPSEEK:
                # DeepSeek uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://api.deepseek.com"
                return ChatOpenAI(**common_params)

            case LLMProvider.DOUBAO:
                # Doubao uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://ark.cn-beijing.volces.com/api/v3/"
                return ChatOpenAI(**common_params)

            case LLMProvider.DASHSCOPE:
                # DashScope uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                return ChatOpenAI(**common_params)

            case LLMProvider.LINGXI:
                # Lingxi uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                return ChatOpenAI(**common_params)

            case LLMProvider.KIMI:
                # Kimi uses OpenAI-compatible API
                if not self.model_config.base_url:
                    common_params["base_url"] = "https://api.moonshot.cn/v1"
                return ChatOpenAI(**common_params)

            case LLMProvider.AZURE:
                # Azure OpenAI
                azure_params = {
                    "azure_deployment": self.model_config.model,
                    "temperature": self.model_config.temperature,
                    "max_tokens": self.model_config.max_tokens,
                    "max_retries": self.model_config.max_retries,
                }
                if self.model_config.api_key:
                    azure_params["api_key"] = self.model_config.api_key
                if self.model_config.base_url:
                    azure_params["azure_endpoint"] = self.model_config.base_url
                return ChatOpenAI(**azure_params)

            case _:
                raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables."""
        env_keys = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
            LLMProvider.DOUBAO: "DOUBAO_API_KEY",
            LLMProvider.DASHSCOPE: "DASHSCOPE_API_KEY",
            LLMProvider.LINGXI: "LINGXI_API_KEY",
            LLMProvider.KIMI: "KIMI_API_KEY",
            LLMProvider.OPENROUTER: "OPENROUTER_API_KEY",
            LLMProvider.AZURE: "AZURE_OPENAI_API_KEY",
        }
        return os.getenv(env_keys.get(self.provider, ""))

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM asynchronously with optional tools."""
        if tools:
            # Bind tools to the model
            model_with_tools = self._client.bind_tools(tools)
            return await model_with_tools.ainvoke(messages, **kwargs)
        else:
            return await self._client.ainvoke(messages, **kwargs)

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM synchronously with optional tools."""
        if tools:
            # Bind tools to the model
            model_with_tools = self._client.bind_tools(tools)
            return model_with_tools.invoke(messages, **kwargs)
        else:
            return self._client.invoke(messages, **kwargs)

    @property
    def client(self) -> BaseLanguageModel:
        """Get the underlying LangChain client."""
        return self._client

    @property
    def provider_name(self) -> str:
        """Get the provider name as string."""
        return self.provider.value