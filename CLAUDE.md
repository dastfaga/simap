# simap Projekt

## Ziel

Regelmässig (wöchentlich/monatlich) öffentliche Ausschreibungen von simap.ch
automatisiert auslesen, filtern und bewerten, um Cross-Selling-Chancen zu
erkennen (Beispiel: Bauausschreibung erwähnt kein Lüftung/Klima/Kälte/Heizung
→ Auftraggeber proaktiv anschreiben: "hast du das vergessen?").

## Was (Scoring)

Zwei unabhängige Scores pro Treffer, **kein Addieren — Max-Score zählt**:

**PubType-Score** (wie "heiss"/aktionierbar die Phase ist):
| Typ | Punkte |
|---|---|
| tender | 10 |
| request_for_information | 7 |
| study_contract | 3 |
| competition | 2 |
| advance_notice | 1 |

Ausgeschlossen (zu spät / nicht zugänglich für externe Anbieter):
award_tender, award_study_contract, award_competition, direct_award,
participant_selection, revocation, abandonment, selective_offering_phase.

**Keyword-Score** (Textsuche in Publikationsdetails):
| Keyword | Punkte |
|---|---|
| Lüftung | 10 |
| Klima | 8 |
| Kälte | 6 |
| Heizung | 4 |
| Haustechnik | 3 |
| Gebäudetechnik | 3 |
| (keines) | 0 |

## Wie

- Öffentliche REST-API (`https://www.simap.ch/api`), **keine Authentifizierung
  nötig** für Suche/Details/Referenzdaten
- Komplette OpenAPI-Spec lokal: [docs/simap-openapi.yaml](docs/simap-openapi.yaml)
- Hauptskript: [scripts/fetch_simap.py](scripts/fetch_simap.py)
  - sucht via `/publications/v2/project/project-search` (volle Pagination über `lastItem`)
  - holt pro Treffer Details via `/publications/v1/project/{id}/publication-details/{id}`
  - extrahiert Auftraggeber-Kontakt (Name/Mail/Telefon) direkt aus den Daten
  - baut fertigen `mailto:`-Link (Betreff + Text vorausgefüllt)

## Wo

- Kantone (fix, Kundenwunsch): **BS, BL, AG, SO**
- Firma: fagaklima.ch (Klimatechnik/HLK)

## Warum

- Auftraggeber-Kontaktdaten sind direkt in den simap-Publikationsdetails
  enthalten (`project-info.procOfficeAddress.email`) — kein manuelles
  Zuordnen nötig
- Mail-Empfänger = Auftraggeber selbst (nicht intern), Ziel ist aktive
  Kundenansprache, keine interne Verteilung

## Mail-Versand — final gelöst (funktioniert, getestet)

**Zwei getrennte Mail-Flows, nicht verwechseln:**

1. **Wochenreport AN den Nutzer** (Liste aller Treffer, sortiert nach Score):
   läuft über den **Gmail-Connector** (OAuth, kein App-Passwort/SMTP nötig),
   Konto `dastfaga@gmail.com` (privates Gmail des Nutzers), sendet direkt an
   `damir.stojadinovic@fagaklima.ch`. Live getestet und bestätigt angekommen
   (2026-10-07, echte simap-Daten, 6 Treffer). Tool:
   `mcp__<gmail-connector-id>__send_message` (Connector-ID ändert sich bei
   Reconnect — über `ToolSearch query:"gmail send"` neu auflösen).
   **Format: HTML-Tabelle** (nicht Fliesstext) — Spalten: Score, Titel,
   Auftraggeber, Kanton, Distanz, Anfrage (mailto-Link), simap-Link.
   Sortiert nach Score absteigend, nichts wird verworfen.
   Mailto-Link pro Treffer **mit vorausgefülltem Betreff+Text** (Nutzer
   will das so — nicht leer lassen). Skript dafür:
   [scripts/build_report_html.py](scripts/build_report_html.py) baut nur das
   HTML (kein Versand), der Versand selbst läuft über den Gmail-Tool-Call.
   Format final bestätigt am 2026-10-07 ("perfekt, festhalten").

   **Score-Farbskala:** nur die **Score-Zahl selbst farbig** (`<b style="color:...">`),
   **kein Zeilen-/Zellenhintergrund** — Hintergrundfarben auf `<tr>` werden vom
   Gmail-Sanitizer beim Versand entfernt (siehe Falle unten), und selbst auf
   `<td>` gesetzt wirkten sie im Dark Mode des Empfängers schwarz/unlesbar.
   Grenzen (`GREEN_FROM=24`, `ORANGE_FROM=14`, sonst rot) sind vorläufig,
   Farbwerte kräftig/dark-mode-fest gewählt (`#1a8a1a` grün, `#b36b00` orange,
   `#c0392b` rot), nicht die hellen Pastelltöne.

   **Wichtige Fallen (schon reingetreten, nicht wiederholen):**
   - `htmlBody` beim `send_message`-Tool-Call immer als **echtes HTML**
     übergeben (`<p>`, `<a href="...">`), NIEMALS als escapte Entities
     (`&lt;p&gt;`) — sonst kommt nur sichtbarer Text an, Mailprogramme linken
     daraus bestenfalls automatisch die nackte Adresse (ohne Betreff/Text).
   - `style="..."` auf `<tr>` wird beim Senden entfernt (Gmail-Sanitizer) —
     Styling nur auf `<td>`/`<b>`/`<span>` setzen, nie auf `<tr>`.
   Grund für Gmail statt fagaklima.ch: Office 365 Graph API braucht
   Admin-Rechte (Nutzer hat keine, admin.microsoft.com und
   entra.microsoft.com beide blockiert), SMTP mit Passwort ist von
   Microsoft seit 2022 deaktiviert. Gmail-Connector umgeht beides komplett
   (normaler OAuth-Login).

2. **Einzelne Anfragen AN die Auftraggeber** (die eigentlichen
   Akquise-Mails): gehen **automatisch aus `damir.stojadinovic@fagaklima.ch`**,
   weil der Nutzer diese selbst über sein in Outlook konfiguriertes
   Geschäftskonto verschickt (manuell, nach Durchsicht der Liste aus Flow 1).
   Hierfür ist **kein** Gmail/Graph-API-Zugriff nötig.

Mails an Auftraggeber gehen **nie automatisch direkt raus** — Nutzer sichtet
die Liste selbst und entscheidet pro Treffer, ob/was er schreibt.

## Wann

- Keine feste Automatisierung/Scheduling bisher eingerichtet — noch in der
  Testphase (manuelle Skriptläufe). Takt (wöchentlich/monatlich) wird nach
  Abschluss der Scoring-Tests festgelegt.

**Standort-Score** (Nähe zum Firmensitz, Helsinkistrasse 12, 4142 Münchenstein):
| Bedingung | Punkte |
|---|---|
| Kanton BS oder BL | 10 (kein Maps-Call nötig, Kanton reicht) |
| Kanton AG/SO, Fahrdistanz ≤ 50 km | 6 |
| Kanton AG/SO, Fahrdistanz > 50 km | 3 |

Fahrdistanz = echte Autolinie via OSRM (`router.project-osrm.org`, kostenloser
Demo-Server, kein Login), nicht Luftlinie. Luftlinie wird als Zusatzfeld
(`distanceKm`) trotzdem mitgespeichert.

## Gesamtscore

`Gesamtscore = PubType-Score + Keyword-Score + Standort-Score` (addiert,
max. 10+10+10 = 30 Punkte). Innerhalb des Keyword-Scores bleibt die Max-Regel
bestehen (z.B. Lüftung UND Heizung im selben Text ergibt trotzdem nur 10,
nicht 14) — nur die drei Gruppen werden addiert, nicht die Keywords
untereinander.

**Alarm-Schwellenwert:** `>= 24` (Datei: `ALARM_THRESHOLD` in
`scripts/fetch_simap.py`). **Vorläufig/provisorisch** — alte Regel war `>= 17`
auf der alten 20er-Skala (vor Standort-Score), wurde proportional auf die neue
30er-Skala hochgesetzt. Nutzer will das später genauer definieren.

## Status (Stand 2026-10-07)

| # | Punkt | Status |
|---|---|---|
| 1 | Datenabfrage (simap API) | fertig, getestet |
| 2 | Detailabruf (Kontakt etc.) | fertig, getestet |
| 3 | Scoring (3 Dimensionen) | fertig, getestet |
| 4 | Alarm-Flag | funktioniert, Schwellenwert (24) nur Platzhalter |
| 5 | Sortierung nach Score | fertig, getestet |
| 6 | Mailto-Link (Empfänger+Betreff+Text) | fertig, bestätigt funktionierend |
| 7 | Report als HTML-Tabelle zusammenbauen | fertig, bestätigt ("genau so") |
| 8 | Versand an Nutzer (Gmail-Connector) | fertig, bestätigt angekommen |
| 9 | Manueller Schritt (Nutzer klickt/prüft/sendet) | Mechanismus steht |
| 10 | Automatisierung/Zeitplan (Scheduling) | **offen** |

## Noch offen / nicht final entschieden

- Punkt 10: Scheduling (wöchentlich o.ä.) noch nicht eingerichtet
- Alarm-Schwellenwert (24) ist nur ein Platzhalter, noch nicht final
- KI-Auswertung pro Treffer (Kurzfassung/Relevanz-Text) — noch nicht gebaut
- Excel wurde explizit abgelehnt ("Excel ist Handarbeit") — nicht erneut vorschlagen
