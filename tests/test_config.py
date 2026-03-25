"""Tests for backend/config.py — verifies defaults and type correctness."""

import pytest
import backend.config as config


def test_claude_model_default():
    assert isinstance(config.CLAUDE_MODEL, str)
    assert len(config.CLAUDE_MODEL) > 0


def test_openai_model_default():
    assert isinstance(config.OPENAI_MODEL, str)


def test_max_tokens_is_int():
    assert isinstance(config.LLM_MAX_TOKENS, int)
    assert config.LLM_MAX_TOKENS > 0


def test_api_host_default():
    assert isinstance(config.API_HOST, str)


def test_api_port_is_int():
    assert isinstance(config.API_PORT, int)
    assert 1 <= config.API_PORT <= 65535


def test_api_workers_is_int():
    assert isinstance(config.API_WORKERS, int)
    assert config.API_WORKERS >= 1


def test_rate_limit_enabled_is_bool():
    assert isinstance(config.RATE_LIMIT_ENABLED, bool)


def test_rate_limit_rpm_is_int():
    assert isinstance(config.RATE_LIMIT_REQUESTS_PER_MINUTE, int)
    assert config.RATE_LIMIT_REQUESTS_PER_MINUTE > 0


def test_environment_is_str():
    assert isinstance(config.ENVIRONMENT, str)


def test_debug_is_bool():
    assert isinstance(config.DEBUG, bool)


def test_anthropic_key_is_str():
    assert isinstance(config.ANTHROPIC_API_KEY, str)


def test_openai_key_is_str():
    assert isinstance(config.OPENAI_API_KEY, str)
