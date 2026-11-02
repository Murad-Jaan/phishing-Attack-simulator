"""M2 sandbox sending-domain allowlist: normalization and rejection cases."""

import pytest

from app.services.settings_service import (
    RESERVED_SEND_DOMAINS,
    SettingsValidationError,
    validate_send_domain_allowlist,
)


@pytest.mark.parametrize(
    "entry", ["example.com", "EXAMPLE.com", "  example.com  ", "*.test", " *.test ", "*.invalid", "  *.INVALID"]
)
def test_normalizes_case_and_whitespace(entry):
    result = validate_send_domain_allowlist([entry])
    assert result == [entry.strip().lower()]


def test_preserves_order_of_valid_entries():
    result = validate_send_domain_allowlist(["*.invalid", " example.com "])
    assert result == ["*.invalid", "example.com"]


@pytest.mark.parametrize(
    "bad",
    [
        "paypal.com",
        "example.org",
        "sub.example.com",
        "*.com",
        "*.invalid.example.com",
        "example.com.evil.test",
        "*",
        "*.example.test",
        "example",
        "evil.test",
        ["example.com", 42],
    ],
)
def test_rejects_non_reserved_domains(bad):
    with pytest.raises(SettingsValidationError) as exc:
        validate_send_domain_allowlist(
            bad if isinstance(bad, list) else [bad]
        )
    fields = exc.value.fields
    assert "send_domain_allowlist" in fields


@pytest.mark.parametrize("empty", ["", "   ", "\t"])
def test_rejects_empty_string_entries(empty):
    with pytest.raises(SettingsValidationError) as exc:
        validate_send_domain_allowlist(["example.com", empty])
    assert "send_domain_allowlist" in exc.value.fields


@pytest.mark.parametrize(
    "dups",
    [
        ["example.com", "example.com"],
        ["example.com", " EXAMPLE.com "],
        ["*.test", " *.TEST ", "example.com"],
    ],
)
def test_rejects_duplicates_after_normalization(dups):
    with pytest.raises(SettingsValidationError) as exc:
        validate_send_domain_allowlist(dups)
    fields = exc.value.fields
    assert "send_domain_allowlist" in fields
    assert "Duplicate" in fields["send_domain_allowlist"]


def test_rejects_empty_allowlist():
    with pytest.raises(SettingsValidationError) as exc:
        validate_send_domain_allowlist([])
    assert "cannot be empty" in exc.value.fields["send_domain_allowlist"]


def test_rejects_non_list():
    with pytest.raises(SettingsValidationError):
        validate_send_domain_allowlist("example.com")


def test_reserved_set_matches_approved_assumptions():
    assert RESERVED_SEND_DOMAINS == ("example.com", "*.test", "*.invalid")
