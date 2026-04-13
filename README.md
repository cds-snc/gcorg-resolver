# gc-org-resolver

Resolves free-text Government of Canada organization names to a canonical `gc_orgID`. Takes messy strings like `"CRA"`, `"Bibliothèque et Archives Canada"`, or email addresses like `"user@inspection.gc.ca"` and returns the numeric ID from the [GC Organization Names and Codes dataset](https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/3faaafb4-00e2-4303-947d-ac786b62559f) on open.canada.ca.

## Endpoints

### POST /resolve

Resolve a batch of names. Returns one result per input.

```sh
curl -X POST http://localhost:5000/resolve \
  -H 'Content-Type: application/json' \
  -d '{"names": ["Bibliothèque et Archives Canada", "CRA", "unknown org"]}'
```

```json
{
  "results": [
    {"input": "Bibliothèque et Archives Canada", "gc_orgID": 2262, "harmonized_name": "Library and Archives Canada", "nom_harmonise": "Bibliothèque et Archives Canada", "matched": true},
    {"input": "CRA", "gc_orgID": 2303, "harmonized_name": "Canada Revenue Agency", "nom_harmonise": "Agence du revenu du Canada", "matched": true},
    {"input": "unknown org", "gc_orgID": null, "harmonized_name": null, "nom_harmonise": null, "matched": false}
  ]
}
```

### GET /resolve

Resolve a single name. Returns the `gc_orgID` as plain text, or an empty string on no match. Intended for use with Excel's `WEBSERVICE()` function.

```
GET /resolve?name=CRA
-> 2303
```

Or in Excel:

```
=WEBSERVICE("http://example.com:5000/resolve?name=" & ENCODEURL(A1))
```

### GET /name

Look up the English or French name for a known `gc_orgID`.

```
GET /name?gc_orgID=2222&lang=fr
-> Agriculture et Agroalimentaire Canada
```

Or in Excel:

```
=WEBSERVICE("http://example.com:5000/name?lang=en&gc_orgID=" & A1)
```

## Data

`data/gc_org_aliases.csv` is a curated lookup table of normalized org name variants and their `gc_orgID`. `data/gc_concordance.csv` is a pinned snapshot of the upstream reference standard, updated periodically.

To refresh the concordance snapshot:

```sh
python data/download_reference_standard.py
```