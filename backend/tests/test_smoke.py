"""Basic smoke tests that don't require a live database."""


def test_price_cache_bounded():
    """BoundedCache evicts oldest entry when maxsize is exceeded."""
    from app.api.prices import _BoundedCache

    cache = _BoundedCache(maxsize=2)
    cache.set(1, "a")
    cache.set(2, "b")
    cache.set(3, "c")  # should evict key 1

    assert cache.get(1) is None
    assert cache.get(2) == "b"
    assert cache.get(3) == "c"


def test_price_cache_lru_order():
    """Accessing an entry moves it to the back (most-recently-used)."""
    from app.api.prices import _BoundedCache

    cache = _BoundedCache(maxsize=2)
    cache.set(1, "a")
    cache.set(2, "b")
    cache.get(1)  # touch key 1 — now key 2 is least recently used
    cache.set(3, "c")  # should evict key 2, not key 1

    assert cache.get(1) == "a"
    assert cache.get(2) is None
    assert cache.get(3) == "c"
