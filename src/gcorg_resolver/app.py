"""Flask REST API for resolving free-text GC org names to ``gc_orgID``."""

import os

from flask import Flask, jsonify, request, send_from_directory

from gcorg_resolver.load_reference_standard import lookup
from gcorg_resolver.resolver import resolve

# Limit in a single API call
MAX_NAMES = 1000
MAX_CONTENT_LENGTH = 512 * 1024  # 512 KB

# Mapping from canonical field name to (english_attr, french_attr) on Org.
_FIELD_ATTRS = {
    "name": ("harmonized_name", "nom_harmonise"),
    "abbreviation": ("abbreviation", "abreviation"),
    "legal_title": ("legal_title", "appellation_legale"),
}

# Synonyms that fold onto a canonical field name.
_FIELD_SYNONYMS = {
    "nom": "name",
    "abreviation": "abbreviation",  # common single-r misspelling
    "appellation_legale": "legal_title",
    "appellation_légale": "legal_title",
}

_VALID_FIELDS = ", ".join(_FIELD_ATTRS)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # CORS: this API is intended to be consumed from arbitrary origins
    # (Excel, Google Sheets, third-party web pages, etc.), so we allow any
    # origin. We answer the browser's OPTIONS preflight ourselves rather
    # than pulling in flask-cors as a dependency.
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    @app.route("/<path:_path>", methods=["OPTIONS"])
    @app.route("/", methods=["OPTIONS"])
    def cors_preflight(_path=""):
        return ("", 204)

    # POST /resolve
    #
    # Accepts a JSON object with a "names" key containing a list of
    # free-text organization name strings. Returns a JSON object with a
    # "results" list, one entry per input. Each entry contains the original
    # input, the matched gc_orgID, the harmonized English and French names,
    # and a boolean indicating whether a match was found.
    #
    # Example request:
    #   {"names": ["Bibliothèque et Archives Canada", "CRA"]}
    #
    # Example response:
    #   {"results": [
    #     {"input": "...", "gc_orgID": 2262, "harmonized_name": "...",
    #      "nom_harmonise": "...", "matched": true},
    #     ...
    #   ]}
    @app.post("/resolve")
    def resolve_names():
        body = request.get_json(silent=True)
        if body is None or not isinstance(body, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        names = body.get("names")
        if not isinstance(names, list):
            return jsonify({"error": "'names' must be a list of strings"}), 400
        if len(names) == 0:
            return jsonify({"error": "'names' must not be empty"}), 400
        if len(names) > MAX_NAMES:
            return (
                jsonify({"error": f"Too many names (max {MAX_NAMES})"}),
                400,
            )

        results = []
        for name in names:
            gc_org_id = resolve(name)
            if gc_org_id is not None:
                org = lookup(gc_org_id)
                results.append(
                    {
                        "input": name,
                        "gc_orgID": org.gc_orgID,
                        "harmonized_name": org.harmonized_name,
                        "nom_harmonise": org.nom_harmonise,
                        "abbreviation": org.abbreviation,
                        "abreviation": org.abreviation,
                        "legal_title": org.legal_title,
                        "appellation_legale": org.appellation_legale,
                        "matched": True,
                    }
                )
            else:
                results.append(
                    {
                        "input": name,
                        "gc_orgID": None,
                        "harmonized_name": None,
                        "nom_harmonise": None,
                        "abbreviation": None,
                        "abreviation": None,
                        "legal_title": None,
                        "appellation_legale": None,
                        "matched": False,
                    }
                )

        return jsonify({"results": results})

    # GET /resolve?name=<org name>
    #
    # Resolves a single organization name passed as a query parameter.
    # Returns the gc_orgID as plain text, or an empty string if no match
    # is found. Designed for use with Excel's WEBSERVICE() function:
    #
    #   =WEBSERVICE("http://example.com/resolve?name=" & ENCODEURL(A1))
    @app.get("/resolve")
    def resolve_single():
        name = request.args.get("name", "")
        if not name:
            return "name parameter is required", 400

        gc_org_id = resolve(name)
        if gc_org_id is not None:
            return str(gc_org_id), 200, {"Content-Type": "text/plain"}
        return "", 200, {"Content-Type": "text/plain"}

    # GET /name?gc_orgID=<id>&lang=<language>[&field=<field>]
    #
    # Returns the requested field for the given gc_orgID in either English
    # or French as plain text. The "lang" parameter accepts: "en", "english",
    # "anglais" (English) or "fr", "french", "francais" (French).
    # The optional "field" parameter accepts: "name" (default), "abbreviation",
    # "legal_title", with French synonyms also accepted. Returns 400 if
    # gc_orgID is missing or not a valid integer, if lang is missing or
    # unrecognised, if field is unrecognised, or if gc_orgID does not exist
    # in the reference standard. Returns an empty body (200) when an org has
    # no value for the requested field (e.g. no abbreviation on record).
    #
    # Example:
    #   GET /name?gc_orgID=2222&lang=fr
    #   -> "Agriculture et Agroalimentaire Canada"
    #
    #   GET /name?gc_orgID=2222&lang=en&field=legal_title
    #   -> "Department of Agriculture and Agri-Food"
    #
    # Excel WEBSERVICE() example:
    #   =WEBSERVICE("http://example.com:5000/name?gc_orgID=" & A1 & "&lang=en")
    @app.get("/name")
    def org_name():

        # Convert arguments to lowercase so gc_orgid and gc_orgID and GC_ORGID all work
        args = {k.lower(): v for k, v in request.args.items()}
        raw_id = args.get("gc_orgid", "")
        lang = args.get("lang", "").strip().lower()

        if not raw_id:
            return "gc_orgID parameter is required", 400
        try:
            gc_org_id = int(raw_id)
        except ValueError:
            return "gc_orgID must be an integer", 400

        if lang.lower() in ("en", "english", "anglais"):
            use_french = False
        elif lang.lower() in ("fr", "french", "francais", "français"):
            use_french = True
        else:
            return "lang must be one of: en, fr", 400

        raw_field = args.get("field", "").strip().lower()
        if not raw_field:
            field = "name"
        else:
            field = _FIELD_SYNONYMS.get(raw_field, raw_field)
            if field not in _FIELD_ATTRS:
                return f"field must be one of: {_VALID_FIELDS}", 400

        try:
            org = lookup(gc_org_id)
        except KeyError:
            return f"No organization found for gc_orgID {gc_org_id}", 404

        en_attr, fr_attr = _FIELD_ATTRS[field]
        value = getattr(org, fr_attr if use_french else en_attr)

        return value, 200, {"Content-Type": "text/plain; charset=utf-8"}

    # GET /health
    #
    # Returns {"status": "ok"} with a 200 status code.
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/.well-known/security.txt")
    def send_security_txt():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "security.txt",
            mimetype="text/plain",
        )

    @app.route("/")
    def send_index():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "index_en.html",
            mimetype="text/html",
        )

    @app.route("/en")
    def send_index_en():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "index_en.html",
            mimetype="text/html",
        )

    @app.route("/fr")
    def send_index_fr():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "index_fr.html",
            mimetype="text/html",
        )

    @app.route("/examples/suggest")
    def send_example_suggest():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "example_suggest.html",
            mimetype="text/html",
        )

    @app.route("/examples/infer")
    def send_example_infer():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "example_infer.html",
            mimetype="text/html",
        )

    return app
