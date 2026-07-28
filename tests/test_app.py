import pytest

from gcorg_resolver.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_resolve_known_names(client):
    resp = client.post(
        "/resolve",
        json={
            "names": ["Agriculture and Agri-Food Canada", "CRA"],
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results) == 2
    assert results[0]["gc_orgID"] == 2222
    assert results[0]["matched"] is True
    assert results[0]["harmonized_name"] == "Agriculture and Agri-Food Canada"
    assert results[0]["abbreviation"] == "AAFC"
    assert results[0]["abreviation"] == "AAC"
    assert results[1]["gc_orgID"] == 2303
    assert results[1]["matched"] is True


def test_resolve_unknown_name(client):
    resp = client.post(
        "/resolve",
        json={
            "names": ["department of unicorns"],
        },
    )
    assert resp.status_code == 200
    result = resp.get_json()["results"][0]
    assert result["gc_orgID"] is None
    assert result["harmonized_name"] is None
    assert result["nom_harmonise"] is None
    assert result["abbreviation"] is None
    assert result["abreviation"] is None
    assert result["matched"] is False


def test_resolve_mixed_known_and_unknown(client):
    resp = client.post(
        "/resolve",
        json={
            "names": ["AAFC", "department of unicorns"],
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert results[0]["matched"] is True
    assert results[0]["gc_orgID"] == 2222
    assert results[1]["matched"] is False


def test_resolve_empty_list_returns_400(client):
    resp = client.post("/resolve", json={"names": []})
    assert resp.status_code == 400
    assert "empty" in resp.get_json()["error"].lower()


def test_resolve_missing_names_key_returns_400(client):
    resp = client.post("/resolve", json={"foo": ["bar"]})
    assert resp.status_code == 400


def test_resolve_oversized_list_returns_400(client):
    resp = client.post(
        "/resolve",
        json={
            "names": ["x"] * 1001,
        },
    )
    assert resp.status_code == 400
    assert "max" in resp.get_json()["error"].lower()


def test_resolve_non_json_returns_400(client):
    resp = client.post(
        "/resolve",
        data="not json",
        content_type="text/plain",
    )
    assert resp.status_code == 400


def test_get_resolve_known_name(client):
    resp = client.get("/resolve?name=CRA")
    assert resp.status_code == 200
    assert resp.data == b"2303"


def test_get_resolve_unknown_name(client):
    resp = client.get("/resolve?name=department+of+unicorns")
    assert resp.status_code == 200
    assert resp.data == b""


def test_get_resolve_missing_param_returns_400(client):
    resp = client.get("/resolve")
    assert resp.status_code == 400


def test_name_returns_english(client):
    assert (
        client.get("/name?gc_orgID=2222&lang=en").data
        == b"Agriculture and Agri-Food Canada"
    )
    assert (
        client.get("/name?gc_orgID=2222&lang=english").data
        == b"Agriculture and Agri-Food Canada"
    )
    assert (
        client.get("/name?gc_orgID=2222&lang=anglais").data
        == b"Agriculture and Agri-Food Canada"
    )


def test_name_returns_french(client):
    assert (
        client.get("/name?gc_orgID=2222&lang=fr").data
        == b"Agriculture et Agroalimentaire Canada"
    )
    assert (
        client.get("/name?gc_orgID=2222&lang=french").data
        == b"Agriculture et Agroalimentaire Canada"
    )
    assert (
        client.get("/name?gc_orgID=2222&lang=francais").data
        == b"Agriculture et Agroalimentaire Canada"
    )
    assert (
        client.get("/name?gc_orgID=2222&lang=français").data
        == b"Agriculture et Agroalimentaire Canada"
    )


def test_name_missing_gc_org_id_returns_400(client):
    assert client.get("/name?lang=en").status_code == 400


def test_name_missing_lang_returns_400(client):
    assert client.get("/name?gc_orgID=2222").status_code == 400


def test_name_invalid_gc_org_id_returns_400(client):
    assert client.get("/name?gc_orgID=abc&lang=en").status_code == 400


def test_name_unrecognised_lang_returns_400(client):
    assert client.get("/name?gc_orgID=2222&lang=de").status_code == 400


def test_name_unknown_gc_org_id_returns_404(client):
    assert client.get("/name?gc_orgID=9999999&lang=en").status_code == 404


def test_name_query_params_are_case_insensitive(client):
    assert (
        client.get("/name?gc_orgid=2222&lang=en").data
        == b"Agriculture and Agri-Food Canada"
    )
    assert (
        client.get("/name?GC_ORGID=2222&LANG=fr").data
        == b"Agriculture et Agroalimentaire Canada"
    )


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# --- field= parameter on GET /name ---


def test_name_field_absent_defaults_to_name(client):
    resp = client.get("/name?gc_orgID=2222&lang=en")
    assert resp.status_code == 200
    assert resp.data == b"Agriculture and Agri-Food Canada"


def test_name_field_name_explicit(client):
    resp = client.get("/name?gc_orgID=2222&lang=en&field=name")
    assert resp.status_code == 200
    assert resp.data == b"Agriculture and Agri-Food Canada"


def test_name_field_abbreviation_en(client):
    resp = client.get("/name?gc_orgID=2222&lang=en&field=abbreviation")
    assert resp.status_code == 200
    assert resp.data == b"AAFC"


def test_name_field_abbreviation_fr(client):
    resp = client.get("/name?gc_orgID=2222&lang=fr&field=abbreviation")
    assert resp.status_code == 200
    assert resp.data == b"AAC"


def test_name_field_legal_title_en(client):
    resp = client.get("/name?gc_orgID=2222&lang=en&field=legal_title")
    assert resp.status_code == 200
    assert resp.data == b"Department of Agriculture and Agri-Food"


def test_name_field_legal_title_fr(client):
    resp = client.get("/name?gc_orgID=2222&lang=fr&field=legal_title")
    assert resp.status_code == 200
    assert resp.data == "Ministère de l’Agriculture et de l’Agroalimentaire".encode()


def test_name_field_unrecognised_returns_400(client):
    resp = client.get("/name?gc_orgID=2222&lang=en&field=abbrevation")
    assert resp.status_code == 400
    assert "field must be one of" in resp.data.decode()


def test_name_field_french_synonym_abreviation(client):
    resp = client.get("/name?gc_orgID=2222&lang=fr&field=abreviation")
    assert resp.status_code == 200
    assert resp.data == b"AAC"


def test_name_field_french_synonym_appellation_legale(client):
    resp = client.get("/name?gc_orgID=2222&lang=fr&field=appellation_legale")
    assert resp.status_code == 200
    assert resp.data == "Ministère de l’Agriculture et de l’Agroalimentaire".encode()


def test_name_field_nom_synonym(client):
    resp = client.get("/name?gc_orgID=2222&lang=en&field=nom")
    assert resp.status_code == 200
    assert resp.data == b"Agriculture and Agri-Food Canada"


def test_name_field_abbreviation_empty_org_returns_200(client):
    """Org 2270 has no abbreviation on record; should return 200 with empty body."""
    resp = client.get("/name?gc_orgID=2270&lang=en&field=abbreviation")
    assert resp.status_code == 200
    assert resp.data == b""


# --- POST /resolve new keys ---


def test_post_resolve_includes_legal_title_fields(client):
    resp = client.post("/resolve", json={"names": ["Agriculture and Agri-Food Canada"]})
    assert resp.status_code == 200
    result = resp.get_json()["results"][0]
    assert result["matched"] is True
    assert result["legal_title"] == "Department of Agriculture and Agri-Food"
    assert "appellation_legale" in result
    assert result["appellation_legale"] != ""


def test_post_resolve_unmatched_legal_title_null(client):
    resp = client.post("/resolve", json={"names": ["Department of Unicorns"]})
    assert resp.status_code == 200
    result = resp.get_json()["results"][0]
    assert result["matched"] is False
    assert result["legal_title"] is None
    assert result["appellation_legale"] is None
