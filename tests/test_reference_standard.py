from gc_org_resolver.load_reference_standard import load_reference_standard, lookup


def test_load_gcorgs_refstd_returns_many_orgs():
    orgs = load_reference_standard()
    assert len(orgs) > 100
    assert all(isinstance(o.gc_orgID, int) for o in orgs)


def test_aafc_loads_with_expected_fields():
    aafc = lookup(2222)
    assert aafc.harmonized_name == "Agriculture and Agri-Food Canada"
    assert aafc.nom_harmonise == "Agriculture et Agroalimentaire Canada"
    assert aafc.abbreviation == "AAFC"
    assert aafc.abreviation == "AAC"


def test_name_variants_returns_four_forms_for_populated_row():

    aafc = lookup(2222)
    assert aafc.name_variants() == [
        "Agriculture and Agri-Food Canada",
        "Agriculture et Agroalimentaire Canada",
        "AAFC",
        "AAC",
    ]


def test_lookup_is_cached():
    assert lookup(2222) is lookup(2222)


def test_all_gc_org_ids_are_unique():
    orgs = load_reference_standard()
    ids = [o.gc_orgID for o in orgs]
    assert len(ids) == len(set(ids))
