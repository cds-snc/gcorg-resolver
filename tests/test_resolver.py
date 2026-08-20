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
