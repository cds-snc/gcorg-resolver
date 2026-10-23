import pytest

from gcorg_resolver import resolver
from gcorg_resolver.normalize import normalize
from gcorg_resolver.resolver import resolve


def test_resolves_canonical_english_name():
    assert resolve("Agriculture and Agri-Food Canada") == 2222


def test_resolves_canonical_french_name():
    assert resolve("Agriculture et Agroalimentaire Canada") == 2222


def test_resolves_english_abbreviation():
    assert resolve("AAFC") == 2222


def test_normalization_handles_case_and_whitespace():
    assert resolve("  agriculture AND agri-food canada  ") == 2222


def test_csc_resolves_to_correctional_service():
    assert resolve("CSC") == 2255


def test_unknown_org_returns_none():
    assert resolve("department of unicorns") is None


def test_empty_string_returns_none():
    assert resolve("") is None


def test_fuzzy_match_recovers_from_typo_in_long_name():
    assert resolve("Agriculutre and Agri-Food Canada") == 2222


def test_fuzzy_match_recovers_from_missing_word():
    assert resolve("Innovation Science Economic Developement") == 2231


def test_short_query_does_not_fuzzy_match():
    # "csa" is a real abbreviation (Canadian Space Agency); "csz" is not,
    # but it's close enough to both "csa" and "csc" that a fuzzy fallback
    # would pick one. The length gate must keep us honest here.
    assert resolve("csz") is None


def test_long_unrelated_string_returns_none():
    assert resolve("department of completely imaginary unicorns") is None


def test_gc_org_id_resolves_to_itself():
    assert resolve("2222") == 2222
    assert resolve(" 2303 ") == 2303


def test_unknown_gc_org_id_returns_none():
    assert resolve("999999") is None


@pytest.fixture()
def aliases_with_dangling_id(tmp_path, monkeypatch):
    """Point the resolver at an alias file where 999999 is not a known org."""
    aliases = tmp_path / "gc_org_aliases.csv"
    rows = [
        ("Agriculture and Agri-Food Canada", 2222),
        ("Agriculture and Agri-Foods", 999999),
        ("dangling", 999999),
    ]
    aliases.write_text(
        "name,gc_orgID\n" + "".join(f"{normalize(n)},{i}\n" for n, i in rows),
        encoding="utf-8",
    )
    monkeypatch.setattr(resolver, "ALIASES_PATH", aliases)
    resolver._alias_index.cache_clear()
    yield
    resolver._alias_index.cache_clear()


def test_alias_for_org_missing_from_reference_data_is_unmatched(
    aliases_with_dangling_id,
):
    assert resolve("dangling") is None


def test_dangling_exact_hit_does_not_fall_through_to_fuzzy_match(
    aliases_with_dangling_id,
):
    # Close enough to fuzzy-match AAFC, but its own exact alias is dead
    assert resolve("Agriculture and Agri-Foods") is None


def test_live_alias_still_resolves_beside_dangling_ones(aliases_with_dangling_id):
    assert resolve("Agriculture and Agri-Food Canada") == 2222
