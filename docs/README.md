# simap.ch API Dokumentation

Lokale Ablage der offiziellen API-Doku der neuen simap.ch-Plattform (Schweizer Beschaffungswesen / KISSimap.ch), abgerufen am 2026-10-07.

## Dateien

- [simap-openapi.yaml](simap-openapi.yaml) — vollständige OpenAPI-3.0.3-Spec (Version 1.5.1), Quelle: `https://www.simap.ch/api/specifications/simap.yaml`
- [simap-api-changelog.html](simap-api-changelog.html) — Changelog der API-Version
- [simap-oauth-quickguide.pdf](simap-oauth-quickguide.pdf) — Quick Guide zum OAuth Authorization Code Flow

## Zugriff / Quellen

- Swagger UI: https://www.simap.ch/api-doc/
- Base URL: `https://www.simap.ch/api`
- Auth: OAuth2 Authorization Code Flow (siehe PDF); einzelne öffentliche Endpunkte (Suche, Details, Referenzdaten) sind laut Community-Quellen ohne Authentifizierung aufrufbar (`security: []`).

## Grobe Struktur (Tags/Ressourcen)

Die Spec deckt die komplette Plattform ab, u. a.:

- **Publikationen / Projekte**: `publications/*`, `pub-drafts/*` (Ausschreibungen anlegen, Lose, Kriterien, Fristen, Zuschlag, Widerruf, Korrektur)
- **Suche**: `publications/v2/project/project-search` (öffentliche Volltextsuche, Pflichtparameter `lang`)
- **Projektdokumente**: `project-documents/*` (Download, ZIP-Token)
- **Vergabestellen (Procurement Offices)**: `procoffices/*` (inkl. `po/public` für das öffentliche Verzeichnis)
- **Kompetenzzentren**: `compcentres/*`
- **Institutionen**: `institutions/*`
- **Referenzdaten/Codes**: `codes/*` (CPV, BKP, eBKP-H/T, NPK, OAG, CPC), `cantons`, `countries`, `languages`, `activities`, `criteria`

Insgesamt 224 Pfade. Für einen schnellen Überblick:

```bash
grep -E "^  /" simap-openapi.yaml
```

## Hinweis

Laut Swagger-UI-Beschreibung können sich INT- und PROD-Umgebung leicht unterscheiden (neue Funktionen erscheinen zuerst auf INT). Vor Produktivnutzung Changelog und beide Umgebungen vergleichen.
