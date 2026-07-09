import pytest

from gcorg_resolver.normalize import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Innovation, Science and Economic Development Canada",
            "innovation science economic development",
        ),
        (
            "Bibliothèque et Archives Canada",
            "bibliotheque archives",
        ),
        (
            "Femmes et Égalité des genres Canada",
            "femmes egalite genres",
        ),
        (
            "Canada Revenue Agency / Agence du revenu du Canada",
            "revenue agency agence revenu",
        ),
    ],
)
def test_r_docstring_examples(raw: str, expected: str):
    assert normalize(raw) == expected


def test_lowercases_and_strips_diacritics():
    assert normalize("Ministère de l'Emploi") == "emploi"


def test_strips_trailing_canada_variants():
    assert normalize("Department of Finance Canada") == "finance"
    assert normalize("Finances Canada") == "finances"
    assert normalize("Ministère des Finances du Canada") == "finances"


def test_office_prefix_is_stripped():
    assert normalize("Office of the Auditor General of Canada") == "auditor general"


def test_agency_typos_are_fixed():
    assert normalize("Canada Revenue Agnecy") == "revenue agency"
    assert normalize("Canadian Space Ageny") == "space agency"


def test_department_typos_are_fixed():
    assert normalize("Deprtment of Finance") == "finance"


def test_punctuation_collapses():
    assert normalize("Foo & Bar (Baz)") == "foo bar baz"


def test_whitespace_is_squished():
    assert normalize("  Foo   Bar  ") == "foo bar"


def test_empty_string():
    assert normalize("") == ""


def test_bare_canada_is_stripped():
    assert normalize("Canada") == ""


def test_canadian_adjective_is_stripped():
    assert normalize("Canadian Heritage") == "heritage"
    assert (
        normalize("Agence canadienne d'inspection des aliments")
        == "agence inspection aliments"
    )
    assert normalize("Forces canadiennes") == "forces"


def test_canada_inside_domain_is_preserved():
    assert normalize("fintrac-canafe.canada.ca") == "fintrac-canafe.canada.ca"


def test_trailing_inc_is_stripped():
    assert normalize("Marine Atlantic Inc.") == "marine atlantic"
    assert normalize("Marine Atlantic Inc") == "marine atlantic"


def test_non_trailing_inc_is_preserved():
    assert normalize("Inc Holdings Ltd") == "inc holdings ltd"


def test_email_is_stripped_to_domain():
    assert normalize("user@agr.gc.ca") == "agr.gc.ca"
    assert normalize("first.last@inspection.gc.ca") == "inspection.gc.ca"


def test_email_subdomains_are_stripped():
    assert normalize("user@mail.agr.gc.ca") == "agr.gc.ca"
    assert normalize("user@a.b.cra-arc.gc.ca") == "cra-arc.gc.ca"


def test_email_canada_ca_suffix():
    assert normalize("user@sub.fintrac-canafe.canada.ca") == "fintrac-canafe.canada.ca"


def test_email_generic_tld():
    assert normalize("user@sub.example.ca") == "example.ca"


def test_non_email_unchanged():
    assert normalize("Folding @ Home") == "folding @ home"


def test_abbreviation_dots_are_stripped():
    assert normalize("St. John's") == "st john s"
    assert normalize("Intl. Trade") == "intl trade"


def test_domain_dots_are_preserved():
    assert normalize("agr.gc.ca") == "agr.gc.ca"


def test_department_affix_is_stripped_en():
    assert normalize("Department of Indigenous Services") == "indigenous services"
    assert normalize("Indigenous Services Department") == "indigenous services"
    assert normalize("Deparment of Indigenous Services") == "indigenous services"


def test_department_affix_is_stripped_fr():
    assert normalize("Ministère de la Défense nationale") == "defense nationale"
    assert normalize("Ministère des Finances") == "finances"
    assert normalize("Ministère du Patrimoine canadien") == "patrimoine"
    assert normalize("Ministère d'Innovation") == "innovation"
    assert normalize("Cabinet du Premier ministre") == "cabinet premier ministre"


def test_trailing_department_tag_is_stripped():
    assert (
        normalize("Agriculture and Agri-Food (Department of)")
        == "agriculture agri-food"
    )
    assert normalize("Environment (Department of the)") == "environment"


def test_trailing_crown_corporation_tag_is_stripped():
    assert normalize("Marine Atlantic Inc. (Crown Corporation)") == "marine atlantic"
    assert (
        normalize("Export Development Canada (Crown Corporation)")
        == "export development"
    )


def test_trailing_office_tag_is_stripped():
    assert (
        normalize("Governor General's Secretary (Office of the)")
        == "governor general s secretary"
    )


def test_trailing_entity_tag_fr():
    assert normalize("Défense nationale (Ministère de la)") == "defense nationale"
    assert normalize("Finances (Ministère des)") == "finances"
    assert normalize("Patrimoine (Ministère du)") == "patrimoine"


def test_trailing_entity_tag_fr_elided_article():
    assert (
        normalize("Agriculture et de l'Agroalimentaire (Ministère de l')")
        == "agriculture agroalimentaire"
    )
    assert normalize("Environnement (Ministère de l')") == "environnement"
