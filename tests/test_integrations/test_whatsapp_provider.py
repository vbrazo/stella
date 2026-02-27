"""Tests for WhatsApp provider factory and interface compliance."""

from unittest.mock import patch

from app.integrations.whatsapp import client as wa_module
from app.integrations.whatsapp.base import WhatsAppProvider
from app.integrations.whatsapp.cloud_api import CloudAPIProvider
from app.integrations.whatsapp.evolution_api import EvolutionAPIProvider


def test_cloud_api_implements_interface():
    """CloudAPIProvider is a valid WhatsAppProvider."""
    assert issubclass(CloudAPIProvider, WhatsAppProvider)
    provider = CloudAPIProvider()
    for method in ("send_text", "send_buttons", "send_cta_card", "download_media", "mark_as_read"):
        assert hasattr(provider, method)
        assert callable(getattr(provider, method))


def test_evolution_api_implements_interface():
    """EvolutionAPIProvider is a valid WhatsAppProvider."""
    assert issubclass(EvolutionAPIProvider, WhatsAppProvider)
    with patch("app.config.settings") as mock_settings:
        mock_settings.evolution_api_url = "http://localhost:8080"
        mock_settings.evolution_api_key = "test_key"
        mock_settings.evolution_instance_name = "test"
        provider = EvolutionAPIProvider()
    for method in ("send_text", "send_buttons", "send_cta_card", "download_media", "mark_as_read"):
        assert hasattr(provider, method)
        assert callable(getattr(provider, method))


def test_factory_returns_cloud_api_by_default():
    """With default config (cloud_api), factory returns CloudAPIProvider."""
    wa_module._provider = None  # reset singleton
    with patch("app.config.settings") as mock_settings:
        mock_settings.whatsapp_provider = "cloud_api"
        mock_settings.whatsapp_api_version = "v21.0"
        mock_settings.whatsapp_phone_number_id = "123"
        mock_settings.whatsapp_token = "token"
        provider = wa_module._get_provider()
    assert isinstance(provider, CloudAPIProvider)
    wa_module._provider = None  # cleanup


def test_factory_returns_evolution_when_configured():
    """With WHATSAPP_PROVIDER=evolution, factory returns EvolutionAPIProvider."""
    wa_module._provider = None  # reset singleton
    with patch("app.config.settings") as mock_settings:
        mock_settings.whatsapp_provider = "evolution"
        mock_settings.evolution_api_url = "http://localhost:8080"
        mock_settings.evolution_api_key = "test_key"
        mock_settings.evolution_instance_name = "test"
        provider = wa_module._get_provider()
    assert isinstance(provider, EvolutionAPIProvider)
    wa_module._provider = None  # cleanup
