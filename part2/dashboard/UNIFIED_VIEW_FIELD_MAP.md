# GET `/unified` → surfaces des maquettes

**But:** Quand l’API expose `GET /unified` (voir [plan_part2.md](../plan_part2.md) §13, §15), brancher les **vraies** réponses pipeline + IoT sur les zones UI — **sans** afficher du ground truth statique comme s’il venait de l’extraction en direct.

**Schéma documents (déjà aligné pipeline) :** [`../pipeline/energy_extract/models.py`](../pipeline/energy_extract/models.py) — `ExtractedDocument`, `ElectricityMeter`, `ElectricitySlotRow`, `GasBillFields`, `WaterBillFields`, `ScadaAlarm`.

---

## 1. Enveloppe JSON recommandée pour `/unified` (contrat logique)

Structure indicative (à implémenter côté FastAPI) pour alimenter **toutes** les maquettes :

| Clé | Type | Rôle |
|-----|------|------|
| `generated_at` | string ISO8601 | Horodatage réponse API |
| `health` | object | Miroir ou lien vers `/health` (broker, DB, dernière ingest) |
| `documents` | array of `ExtractedDocument` | Liste des derniers documents ingérés / normalisés |
| `validation_summary` | object | Compteurs warnings, erreurs bloquantes, dernière validation |
| `normalized_rollups` | object | Totaux kWh / CO₂ / coûts agrégés **dérivés** des documents + facteurs versionnés |
| `iot_period_aggregates` | array | Une entrée par fenêtre `period_start`–`period_end` : moyenne `temp_c`, max `‖accel‖`, taux `edge_anomaly`, stats de gaps |
| `iot_live_strip` | array | Dernières N minutes : points `{ timestamp, temp_c, accel_norm, edge_anomaly }` (données MQTT persistées, pas GT) |
| `openapi_url` | string | URL `/docs` pour lien UI |

Les champs internes de `ExtractedDocument` utilisés au dashboard :

- `parser_path`, `prompt_version`, `confidence_0_1`, `raw_warnings`
- `electricity_meters[]` : `ctr_number`, `meter_role`, `rows[]` (`time_slot`, `tariff_code`, `ancien_index`, `nouveau_index`, `delta_active_kwh`, `is_reactive`, `reactive_delta`, …)
- `gas` : `nm3_delta`, `pcs`, `th_total`, `total_cost_ht_tnd`, `total_net_a_payer_ttc_tnd`, …
- `water` : `volume_m3`, frais HT, TTC
- `scada_alarms[]` : `timestamp`, `severity`, `code`, `subsystem`, `message`

---

## 2. Design 1 — Salle des machines

| Zone UI | Source `/unified` |
|---------|-------------------|
| Rail état (broker, `/health`, dernier ingest) | `health` + méta `generated_at` |
| Registres STEG (2 tableaux) | Filtrer `documents` où `document_family == electricity_steg` ; pour chaque `ElectricityMeter`, lignes `rows` avec `is_reactive == false` ; ligne réactive séparée si `is_reactive` / `reactive_delta` |
| Colonne SONEDE + barre split HT | `documents[].water` — barre = `frais_consommation_eau_ht_tnd` vs `frais_assainissement_ht_tnd` (proportions **calculées**, pas 54/46 figé) |
| Échelle normalisation gaz | `documents[].gas` : enchaîner NM³, PCS, TH, facteur TH→kWh (`factor_source` quand exposé), CO₂ |
| Ticker SCADA gauche | Aplatir `documents[].scada_alarms` ou endpoint dédié ; `severity` → épaisseur bordure |
| Bandeau MQTT bas | `iot_live_strip` ; marqueurs anomalie = `edge_anomaly == true` |
| Lien OpenAPI | `openapi_url` |

---

## 3. Design 2 — Relevé ouvert

| Zone UI | Source `/unified` |
|---------|-------------------|
| Chiffre héros + créneaux (spark strips) | `normalized_rollups` ou somme des `delta_active_kwh` par slot sur le CTR injection ; **ne pas** mélanger réactif |
| Sous-titres / légendes | `parser_path`, `period_label`, `confidence_0_1` |
| Infographie gaz | `gas.th_total` (longueur barre principale), `nm3_delta` + `pcs` en annotation |
| Deux colonnes SONEDE | `water.frais_*` et `total_net_a_payer_ttc_tnd` |
| Pied SCADA collant | Derniers `scada_alarms` + file « pending » si modèle sépare alarmes basses |
| Rail sombre JSON | Derniers messages bruts MQTT **ou** sérialisation compacte de `iot_live_strip[-k:]` — toujours données reçues, pas GT |

---

## 4. Design 3 — Chronologie unifiée

| Zone UI | Source `/unified` |
|---------|-------------------|
| Nœuds sur la spine | Un nœud par `ExtractedDocument` (ou par période fusionnée) avec `period_start`, `period_end`, `document_family` |
| Branches détail (parser, validation) | `parser_path`, `raw_warnings`, `confidence_0_1` |
| Rubans 4 créneaux | `electricity_meters` filtré par rôle ; largeurs ∝ `delta_active_kwh` par `time_slot` |
| Footnote CO₂ gaz | `normalized_rollups` ou calcul inline + chaîne `method_note` obligatoire côté API |
| Agrégats IoT sur nœud | Jointure par chevauchement dates : entrée correspondante dans `iot_period_aggregates` |
| Micro-spine bas d’écran | `iot_live_strip` (fenêtre glissante 15 min) |

---

## 5. Hybride clarté + élégance (recommandé jury)

Fichier : [designs/design-hybrid-clarte-elegance.html](designs/design-hybrid-clarte-elegance.html). Même contrat `/unified` que ci-dessus ; répartition visuelle :

| Zone UI | Source `/unified` |
|---------|-------------------|
| Colonne principale (sable) — blocs « Électricité / Gaz / Eau / SCADA » | `documents[]` filtré par famille ; tables = `electricity_meters`, `gas`, `water`, `scada_alarms` |
| Bandeaux « Documents » + sous-titres | `parser_path`, `period_label`, `confidence_0_1`, `raw_warnings` (sous-titre ou pastille) |
| Colonne droite sombre « Télémesure edge » | **Uniquement** MQTT / `iot_live_strip` + `health` — pas de champs facture |
| Statut compact + transcript + bande | `health`, dernier payload ou série `iot_live_strip` |

---

## 6. Règles anti-tromperie (jury / cahier)

1. Les valeurs d’exemple des maquettes HTML sont **décoratives** ; en prod, lier uniquement à `GET /unified` et aux stores MQTT réels.
2. Ne pas pré-remplir l’UI avec les chiffres du fichier « detailed_description » **sauf** en mode dev explicitement étiqueté « fixture / démo ».
3. Conserver **réactif** et **actif** sur des canaux visuels distincts ([plan_part2.md](../plan_part2.md) §7).

---

## 7. Fichiers maquettes

| Fichier | Chemin |
|---------|--------|
| Hub | [designs/index.html](designs/index.html) |
| Hybride jury | [designs/design-hybrid-clarte-elegance.html](designs/design-hybrid-clarte-elegance.html) |
| Design 1 | [designs/design-1-salle-des-machines.html](designs/design-1-salle-des-machines.html) |
| Design 2 | [designs/design-2-releve-ouvert.html](designs/design-2-releve-ouvert.html) |
| Design 3 | [designs/design-3-chronologie-unifiee.html](designs/design-3-chronologie-unifiee.html) |
