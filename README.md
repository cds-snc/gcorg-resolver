# GC Organization Name Resolution API

[A French version of this document is available here](README_fr.md).

Resolves free-text Government of Canada organization names to a canonical `gc_orgID`. 
Takes messy strings like `"CRA"`, `"Bibliothèque et Archives Canada"`, or email 
addresses like `"user@inspection.gc.ca"` and returns the numeric ID from the 
[GC Organization Names and Codes dataset](https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/3faaafb4-00e2-4303-947d-ac786b62559f) on open.canada.ca.

## Usage

For now, the API  can be found at https://gcorgs.cdssandbox.xyz. It is rate limited to 
50 requests per second and no more than 1000 names in one POST.

### POST /resolve

Resolve a batch of names. Returns one result per input.

```sh
curl -X POST https://gcorgs.cdssandbox.xyz/resolve \
  -H 'Content-Type: application/json' \
  -d '{"names": ["Bibliothèque et Archives Canada", "CRA", "Department of Unicorns"]}'
```

```json
{
  "results": [
    {"input": "Bibliothèque et Archives Canada", "gc_orgID": 2262, "harmonized_name": "Library and Archives Canada", "nom_harmonise": "Bibliothèque et Archives Canada", "matched": true},
    {"input": "CRA", "gc_orgID": 2303, "harmonized_name": "Canada Revenue Agency", "nom_harmonise": "Agence du revenu du Canada", "matched": true},
    {"input": "Department of Unicorns", "gc_orgID": null, "harmonized_name": null, "nom_harmonise": null, "matched": false}
  ]
}
```

### GET /resolve and GET /name

Two simplified endpoints intended for use with Excel's `WEBSERVICE()` and Google Sheet's
`IMPORTDATA()` functions.  `GET /resolve` returns the `gc_orgID` as plain text, or an 
empty string on no match. The result can be passed to `GET /name` to resolve to a 
canonical name. The two-step process encourages users to store the unique `gc_orgID` 
alongside the name of the department.

```
GET /resolve?name=Agriculture
-> 2222

GET /name?gc_orgID=2222&lang=en
-> Agriculture and Agri-Food Canada

GET /name?gc_orgID=2222&lang=fr
-> Agriculture et Agroalimentaire Canada
```
## Examples

### Excel

You can use this API from Excel to automatically resolve organizations in a workbook 
without having to use PowerQuery or any external tools. Simply cut and paste the 
formulas below into your workbook.

```
# Returns the gc_orgID of the name in cell A1
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/resolve?name=" & ENCODEURL(A1))

# Returns the English name corresponding to the gc_orgID in cell A2
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/name?lang=en&gc_orgID=" & A2)

# Returns the French name
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/name?lang=fr&gc_orgID=" & A2)    
```

Note that the `=WEBSERVICE()` function only works in Excel on Windows. **It does not 
work in Excel for Mac.** This is a limitation of Excel for Mac, not a limitation of this 
project.

### Google Sheets

The same API calls work in Google Sheets, using the `=IMPORTDATA()` function and 
providing a delimiter that doesn't exist in any canonical organization names.

```
# Returns the gc_orgID of the name in cell A1
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/resolve?name=" & ENCODEURL(A1))

# Returns the English name corresponding to the gc_orgID in cell A2
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/name?lang=en&gc_orgID=" & A2, "\")

# Returns the French name
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/name?lang=fr&gc_orgID=" & A2, "\")
```

### Online

You can see some *rudimentary* examples of how to use the API to improve data
quality when collecting information from users here:

* [Suggest a correction to an organization name](https://gcorgs.cdssandbox.xyz/examples/suggest) ([source](src/gcorg_resolver/static/example_suggest.html))
* [Infer an organisation name from a user's email](https://gcorgs.cdssandbox.xyz/examples/infer) ([source](src/gcorg_resolver/static/example_infer.html))