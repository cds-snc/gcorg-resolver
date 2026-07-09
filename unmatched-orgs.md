# Unmatched GC org names (program codes 2026-27)

Departments in the TBS program-codes dataset (`EntityDept_name_Eng`) that the
gcorg-resolver at https://gcorgs.cdssandbox.xyz does not resolve. Source list:
`cp-pc-2627-eng.csv`. Generated during the program-code lookup spec work.

- Distinct department names in dataset: **135**
- Unmatched as-is: **34**
- Auto-resolved by name normalization (reorder `(Department of)`, strip `(Crown Corporation)`): **32**
- **Still unmatched: 2** (central PSPC accounting entities, intentionally left unmapped - see below)

`normalize()` (`src/gcorg_resolver/normalize.py`) now strips a trailing
parenthetical entity-type tag - `(Department of)`, `(Department of the)`,
`(Crown Corporation)`, `(Office of the)`, and the French equivalents -
directly in this repo. Previously this reordering only happened in the
external program-code lookup pipeline before it called the API, so the 21
rows below were never actually resolved by the deployed resolver on a raw
query; they only worked because the caller pre-processed the name first. That
gap is now closed here, and 11 more names that didn't resolve even after that
external pre-processing were added as manual aliases in
`data/gc_org_aliases.csv`.

## Intentionally unmatched

| Dataset name | Program rows | Reason |
|---|---|---|
| Regional Pay Office | 0 | Central PSPC accounting entity - no gcorg_ID, left unmapped |
| Superannuation | 0 | Central PSPC accounting entity - no gcorg_ID, left unmapped |

## Resolved via manual alias (needed a new row in `gc_org_aliases.csv`)

| Dataset name | Program rows | gcorg_ID | Harmonized name |
|---|---|---|---|
| Canadian High Arctic Research Station | 3 | 2318 | Polar Knowledge Canada |
| Canadian Transportation Accident Investigation and Safety Board | 4 | 2309 | Transportation Safety Board of Canada |
| Citizenship and Immigration (Department of) | 22 | 2224 | Immigration, Refugees and Citizenship Canada |
| Foreign Affairs, Trade and Development (Department of) | 18 | 2227 | Global Affairs Canada |
| Industry (Department of) | 23 | 2231 | Innovation, Science and Economic Development Canada |
| Office of the Director of Public Prosecutions | 1 | 2277 | Public Prosecution Service of Canada |
| Offices of the Information and Privacy Commissioners of Canada | 3 | 2282 | Office of the Privacy Commissioner of Canada |
| Public Safety and Emergency Preparedness (Department of) | 22 | 2235 | Public Safety Canada |
| Public Works and Government Services (Department of) | 30 | 2236 | Public Services and Procurement Canada |
| Receiver General | 0 | 2236 | Public Services and Procurement Canada |
| Western Economic Diversification (Department of) | 4 | 2240 | Prairies Economic Development Canada |

## Auto-resolved by normalization (now handled directly by `normalize()`)

| Dataset name | Normalized | gcorg_ID | Harmonized name |
|---|---|---|---|
| Agriculture and Agri-Food (Department of) | Department of Agriculture and Agri-Food | 2222 | Agriculture and Agri-Food Canada |
| Canadian Air Transport Security Authority (CATSA) (Crown Corporation) | Canadian Air Transport Security Authority | 3655 | Canadian Air Transport Security Authority |
| Canadian Heritage (Department of) | Department of Canadian Heritage | 2223 | Canadian Heritage |
| Employment and Social Development (Department of) | Department of Employment and Social Development | 2229 | Employment and Social Development Canada |
| Environment (Department of the) | Department of the Environment | 2237 | Environment and Climate Change Canada |
| Export Development Canada (Crown Corporation) | Export Development Canada | 3640 | Export Development Canada |
| Finance (Department of) | Department of Finance | 2225 | Department of Finance Canada |
| Fisheries and Oceans (Department of) | Department of Fisheries and Oceans | 2226 | Fisheries and Oceans Canada |
| Governor General's Secretary (Office of the) | Office of the Governor General's Secretary | 2278 | Office of the Secretary to the Governor General |
| Health (Department of) | Department of Health | 2228 | Health Canada |
| Housing, Infrastructure and Communities (Department of) | Department of Housing, Infrastructure and Communities | 2269 | Housing, Infrastructure and Communities Canada |
| Indigenous Services Canada (Department of) | Department of Indigenous Services Canada | 2243 | Indigenous Services Canada |
| Justice (Department of) | Department of Justice | 2232 | Department of Justice Canada |
| Marine Atlantic Inc. (Crown Corporation) | Marine Atlantic Inc. | 3658 | Marine Atlantic Inc. |
| National Defence (Department of) | Department of National Defence | 2233 | National Defence |
| Natural Resources (Department of) | Department of Natural Resources | 2234 | Natural Resources Canada |
| Parks Canada Agency (Department of) | Department of Parks Canada Agency | 2315 | Parks Canada |
| Transport (Department of) | Department of Transport | 2238 | Transport Canada |
| VIA HFR – VIA TGF Inc. (Crown Corporation) | VIA HFR – VIA TGF Inc. | 3707 | VIA HFR - VIA TGF Inc. |
| VIA Rail Canada Inc. (Crown Corporation) | VIA Rail Canada Inc. | 3662 | VIA Rail Canada Inc. |
| Veterans Affairs (Department of) | Department of Veterans Affairs | 2239 | Veterans Affairs Canada |
