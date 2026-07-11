"""Home Assistant endpoint/auth-mode resolution contracts."""
from __future__ import annotations

import json
from pathlib import Path

from main import resolve_ha_connection


def test_explicit_url_and_llat_use_direct_core():
    result = resolve_ha_connection(
        configured_url="http://192.168.68.57:8123/",
        long_lived_token="llat-test",
        supervisor_token="supervisor-test",
        is_addon=True,
    )

    assert result == {
        "url": "http://192.168.68.57:8123",
        "token": "llat-test",
        "supervisor_header_token": None,
        "mode": "direct",
    }


def test_llat_without_url_uses_internal_core_hostname():
    result = resolve_ha_connection(
        configured_url="",
        long_lived_token="llat-test",
        supervisor_token="supervisor-test",
        is_addon=True,
    )

    assert result["url"] == "http://homeassistant:8123"
    assert result["token"] == "llat-test"
    assert result["supervisor_header_token"] is None
    assert result["mode"] == "direct"


def test_addon_without_llat_uses_one_coherent_supervisor_auth_mode():
    result = resolve_ha_connection(
        configured_url="http://192.168.68.57:8123",
        long_lived_token="",
        supervisor_token="supervisor-test",
        is_addon=True,
    )

    assert result["url"] == "http://supervisor/core"
    assert result["token"] == "supervisor-test"
    assert result["supervisor_header_token"] == "supervisor-test"
    assert result["mode"] == "supervisor_proxy"


def test_direct_connection_without_credential_is_diagnosable():
    result = resolve_ha_connection(
        configured_url="http://homeassistant.local:8123",
        long_lived_token="",
        supervisor_token="",
        is_addon=False,
    )

    assert result["mode"] == "direct_uncredentialed"
    assert result["token"] == ""


def test_addon_manifest_exposes_optional_ha_url():
    manifest_path = Path(__file__).resolve().parents[2] / "config.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["options"]["ha_url"] == ""
    assert manifest["schema"]["ha_url"] == "str?"
