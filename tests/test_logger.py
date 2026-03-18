"""Tests for utils/logger.py — setup_logging."""

import logging
from unittest.mock import patch

from utils.logger import setup_logging


def test_setup_logging_calls_basicconfig_with_info():
    """setup_logging calls logging.basicConfig with INFO level by default."""
    with patch("utils.logger.logging.basicConfig") as mock_cfg:
        setup_logging()
    mock_cfg.assert_called_once()
    kwargs = mock_cfg.call_args[1]
    assert kwargs["level"] == logging.INFO


def test_setup_logging_explicit_debug():
    with patch("utils.logger.logging.basicConfig") as mock_cfg:
        setup_logging("DEBUG")
    kwargs = mock_cfg.call_args[1]
    assert kwargs["level"] == logging.DEBUG


def test_setup_logging_from_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    with patch("utils.logger.logging.basicConfig") as mock_cfg:
        setup_logging()
    kwargs = mock_cfg.call_args[1]
    assert kwargs["level"] == logging.WARNING


def test_setup_logging_invalid_level_falls_back_to_info():
    with patch("utils.logger.logging.basicConfig") as mock_cfg:
        setup_logging("NOT_A_LEVEL")
    kwargs = mock_cfg.call_args[1]
    assert kwargs["level"] == logging.INFO
