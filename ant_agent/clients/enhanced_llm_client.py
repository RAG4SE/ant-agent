# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Enhanced LLM client with robust retry logic and fallback support."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Union
from enum import Enum

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel

from ant_agent.clients.llm_client import LLMClient
from ant_agent.utils.config import ModelConfig, LLMProvider

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for handling API failures."""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class CircuitBreaker:
    """Circuit breaker to prevent overwhelming failing services."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit breaker is open (failing)."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return False
            return True
        return False

    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_threshold} failures")


class EnhancedLLMClient:
    """Enhanced LLM client with robust retry logic, circuit breaker, and fallback support."""

    def __init__(
        self,
        primary_config: ModelConfig,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 10,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """Initialize enhanced LLM client.

        Args:
            primary_config: Primary model configuration
            retry_strategy: Retry strategy (fixed, exponential, linear)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for retries (seconds)
            max_delay: Maximum delay for retries (seconds)
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Timeout for circuit breaker (seconds)
        """
        self.primary_config = primary_config
        self.retry_strategy = retry_strategy
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            timeout=circuit_breaker_timeout
        )

        # Initialize primary client
        self.primary_client = LLMClient(primary_config)

        # Track current client
        self.current_client = self.primary_client

        # Track retry statistics
        self.retry_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retries": 0,
            "circuit_breaker_activations": 0,
        }

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.retry_strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.retry_strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay * (self.exponential_base ** attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        error_str = str(error).lower()

        # Retry on these errors
        retryable_errors = [
            "404", "429", "500", "502", "503", "504",  # HTTP errors
            "timeout", "connection", "network", "rate limit",
            "unavailable", "overload", "throttle", "quota"
        ]

        # Non-retryable errors
        non_retryable_errors = [
            "401", "403", "invalid", "authentication", "authorization",
            "bad request", "not found"  # Model not found, etc.
        ]

        # Check for non-retryable errors first
        for non_retry in non_retryable_errors:
            if non_retry in error_str:
                return False

        # Check for retryable errors
        for retry in retryable_errors:
            if retry in error_str:
                return True

        # Default to retryable for unknown errors
        return True

    async def _try_invoke_with_retry(
        self,
        client: LLMClient,
        messages: Sequence[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
        **kwargs: Any
    ) -> Optional[AIMessage]:
        """Try to invoke with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                self.retry_stats["total_calls"] += 1

                if attempt > 0:
                    self.retry_stats["retries"] += 1
                    delay = self._calculate_delay(attempt - 1)
                    logger.info(f"Retry attempt {attempt}/{self.max_retries} after {delay:.2f}s delay")
                    await asyncio.sleep(delay)

                # Check circuit breaker
                if self.circuit_breaker.is_open():
                    self.retry_stats["circuit_breaker_activations"] += 1
                    logger.warning(f"Circuit breaker is open, skipping attempt {attempt}")
                    continue

                # Make the call, openai regulates tool_calls should be added to the message
                logger.debug(f"Available tools are {tools}")
                if tools:
                    result = await client.ainvoke(messages, tools=tools, **kwargs)
                else:
                    result = await client.ainvoke(messages, **kwargs)

                # Success!
                self.retry_stats["successful_calls"] += 1
                self.circuit_breaker.record_success()

                if attempt > 0:
                    logger.info(f"Success after {attempt} retries")

                return result

            except Exception as e:
                self.retry_stats["failed_calls"] += 1

                # Log the full message sequence for tool_calls validation errors
                if "tool_call_ids did not have response messages" in str(e).lower():
                    logger.error("=" * 80)
                    logger.error("TOOL CALLS VALIDATION ERROR - Full message sequence:")
                    logger.error("=" * 80)
                    for i, msg in enumerate(messages):
                        tool_calls = getattr(msg, 'tool_calls', None)
                        tool_call_id = getattr(msg, 'tool_call_id', None)
                        content_preview = str(msg.content)[:100] if msg.content else "<empty>"
                        logger.error(f"  [{i}] {msg.__class__.__name__}:")
                        logger.error(f"       tool_calls={tool_calls}")
                        logger.error(f"       tool_call_id={tool_call_id}")
                        logger.error(f"       content_preview='{content_preview}'")
                    logger.error("=" * 80)

                # Check if error is retryable
                if not self._is_retryable_error(e) or attempt == self.max_retries:
                    logger.error(f"Non-retryable error or max retries reached: {e}.")
                    self.circuit_breaker.record_failure()
                    raise e

                logger.warning(f"Retryable error on attempt {attempt + 1}: {e}")
                self.circuit_breaker.record_failure()

        return None

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
        **kwargs: Any
    ) -> AIMessage:
        """Invoke the LLM with robust retry logic and fallback support."""

        # Debug logging for message sequence
        logger.debug(f"Invoking LLM with {len(messages)} messages:")
        for i, msg in enumerate(messages):
            tool_calls = getattr(msg, 'tool_calls', None)
            tool_call_id = getattr(msg, 'tool_call_id', None)
            logger.debug(f"  [{i}] {msg.__class__.__name__}: "
                        f"tool_calls={tool_calls}, "
                        f"tool_call_id={tool_call_id}")

        # Try primary client first
        try:
            result = await self._try_invoke_with_retry(
                self.primary_client, messages, tools, **kwargs
            )
            if result:
                return result
        except Exception as primary_error:
            logger.error(f"Primary client failed: {primary_error}")

            # If no fallbacks configured, raise the original error
            raise primary_error

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
        **kwargs: Any
    ) -> AIMessage:
        """Synchronous invoke (wraps async version)."""
        return asyncio.run(self.ainvoke(messages, tools, **kwargs))

    @property
    def client(self) -> LLMClient:
        """Get the current active client."""
        return self.current_client

    @property
    def provider_name(self) -> str:
        """Get the current provider name."""
        return self.current_client.provider_name

    def get_retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        return self.retry_stats.copy()

    def reset_stats(self):
        """Reset retry statistics."""
        self.retry_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retries": 0,
            "circuit_breaker_activations": 0,
        }


def create_enhanced_client(
    primary_config: ModelConfig,
    **kwargs
) -> EnhancedLLMClient:
    """Factory function to create enhanced client with common fallback configurations."""

    return EnhancedLLMClient(
        primary_config=primary_config,
        **kwargs
    )