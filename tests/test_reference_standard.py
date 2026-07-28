from gcorg_resolver.load_reference_standard import load_reference_standard, lookup


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
    assert aafc.legal_title == "Department of Agriculture and Agri-Food"
    assert (
        aafc.appellation_legale == "Ministère de l’Agriculture et de l’Agroalimentaire"
    )


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


def test_all_concordance_ids_have_org_info_row():
    """Every gc_orgID in the concordance must be present in gc_org_info.csv."""
    import csv

    from gcorg_resolver.load_reference_standard import ORG_INFO_PATH

    orgs = load_reference_standard()
    with ORG_INFO_PATH.open(encoding="utf-8-sig", newline="") as f:
        info_ids = {int(row["gc_orgID"]) for row in csv.DictReader(f)}

    concordance_ids = {o.gc_orgID for o in orgs}
    missing = concordance_ids - info_ids
    assert not missing, (
        f"gc_orgIDs in concordance but missing from gc_org_info: {missing}"
    )


def test_legal_titles_non_empty_for_all_orgs():
    """legal_title and appellation_legale must be non-empty for every org in the snapshot."""
    orgs = load_reference_standard()
    missing_en = [o.gc_orgID for o in orgs if not o.legal_title]
    missing_fr = [o.gc_orgID for o in orgs if not o.appellation_legale]
    assert not missing_en, f"Orgs with blank legal_title: {missing_en}"
    assert not missing_fr, f"Orgs with blank appellation_legale: {missing_fr}"
