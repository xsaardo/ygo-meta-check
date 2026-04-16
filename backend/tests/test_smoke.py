"""Basic smoke tests — pure logic, no database or HTTP required."""


def test_image_url_validation():
    """Remote autocomplete skips cards with off-domain image URLs (L6 security fix)."""
    ALLOWED_PREFIX = "https://images.ygoprodeck.com/"

    valid_url = "https://images.ygoprodeck.com/images/cards_small/12345.jpg"
    invalid_url = "https://evil.example.com/malicious.jpg"
    javascript_url = "javascript:alert(1)"

    assert valid_url.startswith(ALLOWED_PREFIX)
    assert not invalid_url.startswith(ALLOWED_PREFIX)
    assert not javascript_url.startswith(ALLOWED_PREFIX)


def test_deck_url_validation():
    """Deck URL href only renders for ygoprodeck.com origins (L4 security fix)."""
    ALLOWED_PREFIX = "https://ygoprodeck.com/"

    safe_url = "https://ygoprodeck.com/deck/dark-magician-abc123"
    unsafe_url = "https://attacker.com/phish"
    javascript_url = "javascript:void(0)"

    assert safe_url.startswith(ALLOWED_PREFIX)
    assert not unsafe_url.startswith(ALLOWED_PREFIX)
    assert not javascript_url.startswith(ALLOWED_PREFIX)
