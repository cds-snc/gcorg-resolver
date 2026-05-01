# API de résolution des noms d'organisations du gouvernement du Canada

*Ce contenu est traduit automatiquement.*

[La version anglaise est disponible ici](README.md)

Permet de convertir les noms d'organisations du gouvernement du Canada en texte libre en un identifiant canonique `gc_orgID`.

Elle accepte des chaînes de caractères complexes comme « ARC », « Bibliothèque et Archives Canada » ou des adresses courriel comme « user@inspection.gc.ca » et renvoie l'identifiant numérique correspondant dans l'ensemble de données [Noms et codes des organisations du gouvernement du Canada](https://open.canada.ca/data/en/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/3faaafb4-00e2-4303-947d-ac786b62559f) disponible sur ouvert.canada.ca.

## Utilisation

Pour l'instant, l'API est accessible à l'adresse https://gcorgs.cdssandbox.xyz. Le débit est limité à 50 requêtes par seconde et à 1 000 noms maximum par requête POST.

### POST /resolve

Résout un lot de noms. Renvoie un résultat par entrée.

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

### GET /resolve et GET /name

Deux points de terminaison simplifiés destinés à être utilisés avec les fonctions `WEBSERVICE()` d'Excel et
`IMPORTDATA()` de Google Sheets. `GET /resolve` renvoie l'identifiant `gc_orgID` en texte brut, ou une chaîne vide en l'absence de correspondance. Le résultat peut être transmis à `GET /name` pour obtenir un nom canonique. Ce processus en deux étapes encourage les utilisateurs à stocker l'identifiant unique `gc_orgID` avec le nom du département.

```
GET /resolve?name=Agriculture
-> 2222

GET /name?gc_orgID=2222&lang=en
-> Agriculture et Agroalimentaire Canada

GET /name?gc_orgID=2222&lang=fr
-> Agriculture et Agroalimentaire Canada
```

### Excel

Vous pouvez utiliser cette API Excel pour résoudre automatiquement les organisations dans un classeur,

sans avoir à utiliser Power Query ni aucun outil externe. Copiez-collez simplement les
formules ci-dessous dans votre classeur.

```
# Renvoie l'identifiant gc_orgID du nom dans la cellule A1
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/resolve?name=" & ENCODEURL(A1))

# Renvoie le nom anglais correspondant à l'identifiant gc_orgID dans la cellule A2
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/name?lang=en&gc_orgID=" & A2)

# Renvoie le nom français
=WEBSERVICE("https://gcorgs.cdssandbox.xyz/name?lang=fr&gc_orgID=" & A2)

```

Notez que la fonction `=WEBSERVICE()` fonctionne uniquement dans Excel sous Windows. **Elle ne fonctionne pas dans Excel pour Mac.** Il s'agit d'une limitation d'Excel, et non d'une limitation de ce projet.

### Google Sheets

Les mêmes appels d'API fonctionnent dans Google Sheets, en utilisant la fonction `=IMPORTDATA()` et en fournissant un délimiteur qui n'existe dans aucun nom d'organisation canonique.

```
# Renvoie l'identifiant gc_orgID du nom dans la cellule A1
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/resolve?name=" & ENCODEURL(A1))

# Renvoie le nom anglais correspondant à l'identifiant gc_orgID dans la cellule A2
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/name?lang=en&gc_orgID=" & A2, "\")

# Renvoie le nom français
=IMPORTDATA("https://gcorgs.cdssandbox.xyz/name?lang=fr&gc_orgID=" & A2, "\")
```

### En ligne

Vous trouverez ici quelques exemples *rudimentaires* d'utilisation de l'API pour améliorer 
la qualité des données lors de la collecte de renseignements auprès des utilisateurs :

* [Suggérer une correction au nom d'une organisation](https://gcorgs.cdssandbox.xyz/examples/suggest)  ([source](src/gcorg_resolver/static/example_suggest.html))
* [Déduire le nom d'une organisation à partir de l'adresse courriel d'un utilisateur](https://gcorgs.cdssandbox.xyz/examples/infer) ([source](src/gcorg_resolver/static/example_infer.html))