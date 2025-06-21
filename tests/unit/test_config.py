"""Tests for configuration module."""
from src.utils.config import AppConfig


def test_app_config_defaults():
    """Test AppConfig default values."""
    config = AppConfig()
    assert config.debug is False
    assert config.log_level == "INFO"
    assert config.port == 8000


def test_app_config_custom_values():
    """Test AppConfig with custom values."""
    config = AppConfig(debug=True, log_level="DEBUG", port=9000)
    assert config.debug is True
    assert config.log_level == "DEBUG"
    assert config.port == 9000


def test_app_config_dict():
    """Test AppConfig can be converted to dict."""
    config = AppConfig()
    config_dict = config.dict()
    
    assert isinstance(config_dict, dict)
    assert "debug" in config_dict
    assert "log_level" in config_dict
    assert "port" in config_dict 