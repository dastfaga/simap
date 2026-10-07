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
   Grenzen final (2026-10-07): `GREEN_FROM=20`, `ORANGE_FROM=10`, sonst rot.
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

**Alarm-/Farb-Schwellenwert: final (2026-10-07), Alarm = Grün-Schwelle:**
- Grün (Alarm) ≥ 20
- Orange 10–19
- Rot < 10
(Datei: `ALARM_THRESHOLD=20` in `scripts/fetch_simap.py`,
`GREEN_FROM=20`/`ORANGE_FROM=10` in `scripts/build_report_html.py`.)
Minimal möglicher Score ist **4** (PubType min 1 + Keyword min 0 + Standort
min 3) — bleibt trotzdem immer in der Liste, siehe harte Regel unten.

## Status (Stand 2026-10-07)

| # | Punkt | Status |
|---|---|---|
| 1 | Datenabfrage (simap API) | fertig, getestet |
| 2 | Detailabruf (Kontakt etc.) | fertig, getestet |
| 3 | Scoring (3 Dimensionen) | fertig, getestet |
| 4 | Alarm-Flag | fertig, final (≥20, siehe Gesamtscore-Abschnitt) |
| 5 | Sortierung nach Score | fertig, getestet |
| 6 | Mailto-Link (Empfänger+Betreff+Text) | fertig, bestätigt funktionierend |
| 7 | Report als HTML-Tabelle zusammenbauen | fertig, bestätigt ("genau so") |
| 8 | Versand an Nutzer (Gmail-Connector) | fertig, bestätigt angekommen |
| 9 | Manueller Schritt (Nutzer klickt/prüft/sendet) | Mechanismus steht |
| 10 | Automatisierung/Zeitplan (Scheduling) | fertig — Cloud-Routine `trig_01YZPtK7cswmLZZ8nQXKXPLg` |

## Scheduling (Punkt 10, final eingerichtet 2026-10-07)

Cloud-Routine `trig_01YZPtK7cswmLZZ8nQXKXPLg` (https://claude.ai/code/routines/trig_01YZPtK7cswmLZZ8nQXKXPLg),
Cron `0 6 * * 1,4` (Montag+Donnerstag, 06:00 UTC fix — ergibt 7:00 Zürich im
Winter/CET, 8:00 im Sommer/CEST, bewusst so gewählt statt 7+6).
Gmail-MCP-Connector angehängt (`connector_uuid: 2701e52f-b826-4aaf-8b25-11f2a97c98b0`).
Komplett **selbstständiger Prompt** (kein Git-Repo-Zugriff nötig) — enthält die
komplette Scoring-/HTML-/Mailto-Logik aus diesem CLAUDE.md nochmal ausgeschrieben,
da Cloud-Routinen nicht auf lokale Dateien zugreifen können.

**Ablaufplan:**
- 08.10.2026 (Do): Vorab-Test, dynamisches Fenster (noch kein Backfill)
- 12.10.–16.11.2026 (11 Läufe, Mo/Do): Backfill Januar–November 2026, ein Monat pro Lauf
- ab 19.11.2026: Normalbetrieb, dynamisches Fenster ohne Lücke/Duplikat:
  - Donnerstags-Lauf: Fenster = Montag bis Mittwoch (dieser Woche)
  - Montags-Lauf: Fenster = Donnerstag bis Sonntag (letzter Woche)
  - (jeder Tag genau einmal gemeldet, kein Overlap)

Debuggen: `RemoteTrigger action:list_runs trigger_id:trig_01YZPtK7cswmLZZ8nQXKXPLg`
dann `get_run_log` auf den Run.

## KI-Auswertung pro Treffer (Punkt 6, Format final bestätigt 2026-10-07)

Jeder Treffer bekommt zusätzlich zur Tabelle drei weitere Felder, per KI generiert:

**1. Detail-Score** (nur Zahlen/echte Werte, KEINE Erklärung, KEIN Gesamt-Score
wiederholt — der steht schon in eigener Spalte):
Format: `<Verfahrensart> <Score>, <gefundenes Keyword> <Score>, <Kanton> <Score>`
Beispiel: `Ausschreibung 10, Lüftung 10, GR 3`
Verfahrensart-Übersetzung (PROPOSED, noch nicht explizit vom Nutzer abgenickt,
nur widerspruchslos stehen gelassen):
tender→Ausschreibung, request_for_information→Request for Information (RFI),
study_contract→Studienauftrag, competition→Wettbewerb,
advance_notice→Vorankündigung
(= offizielle simap-Begriffe aus deren eigener Publikationsart-Filterliste,
vom Nutzer 2026-10-07 per Screenshot/Paste bestätigt)

**2. Kurzfassung** (mehrzeilig, `<br>` zwischen Gedanken, NICHT den Titel
wiederholen, nur was der Titel nicht schon sagt; Frist-Format knapp:
`Frist DD.MM.YY (X Wo)` statt ausgeschrieben):
Beispiel:
```
Gesamtsanierung mit mehreren Etappen.<br>
Diese Publikation: nur Innenputzarbeiten.<br>
Nebenetappen: Lüftungserneuerung (Radon), Heizungsmodernisierung.<br>
Frist 28.10.26 (3 Wo).
```
Wichtig: nur Lüftung/Klima-relevante Funde erwähnen, NICHT andere Gewerke als
etwas, das "angeboten" werden könnte (fagaklima macht nur Lüftung/Klima, nicht
Heizung) — andere Gewerke höchstens als Kontext in der Kurzfassung, niemals in
der Empfehlung oder im Mailtext.

**3. Empfehlung** (mehrzeilig, Einschätzung ob Lüftung/Klima hier Sinn macht):
Beispiel:
```
Nicht für diese Publikation bieten (falsches Gewerk).<br>
Auftraggeber/Planer kontaktieren wegen Lüftungs-/Heizungs-Etappen.<br>
Evtl. andere Publikation oder noch nicht ausgeschrieben.
```
**Empfehlungs-Logik (Richtlinie, kein Gesetz!)** — Grundprinzipien, bestätigt
vom Nutzer am 2026-10-07:
- Personen brauchen Lüftung in **öffentlichen/kommerziellen Gebäuden** —
  grundsätzlich relevant, wo Menschen sich regelmässig aufhalten
- **EFH (Einfamilienhaus) und MFH (Mehrfamilienhaus)**: beide klar **Ja**
  (vom Nutzer explizit als interessante/wichtige Kategorie hervorgehoben)
- **Serverraum/Rechenzentrum: Ja** (zurückgestuft 2026-10-07 von "Immer" auf
  normales "Ja" — keine Sonderrolle, wie alle anderen Einträge der Richtlinie)
- Die Tabelle unten ist eine **Richtlinie für die KI-Einschätzung, kein
  starrer Algorithmus** — die KI soll im Einzelfall abwägen (z.B. Kontext,
  Grösse, Art der Sanierung berücksichtigen), nicht stur nach Tabelle
  abhaken. Keine Festwerte/harte Regeln daraus ableiten.

| Situation | Tendenz | Begründung |
|---|---|---|
| Neubau Wohn-/Schulgebäude, EFH, MFH | Ja | Komfortlüftung heute Standard; Personen im Gebäude |
| Öffentliche/kommerzielle Gebäude generell | Ja | Personen-Aufenthalt macht Lüftung relevant |
| Fenstersanierung/-ersatz (ohne Lüftungs-Erwähnung) | Ja | Klassischer "vergessen"-Fall — dichtere Hülle braucht mech. Lüftung |
| Fassaden-/Dachsanierung (Hülle komplett erneuert) | Ja | Gleiche Logik wie Fenster |
| Radon-/Schadstoffsanierung | Ja | Mechanische Lüftung oft zwingend |
| Gastroküche/Grossküche | Ja | Hohe Luftwechsel-/Abluftanforderungen |
| Spital/Labor/Reinraum | Ja | Strenge Lüftungsauflagen, oft auch Kälte |
| Kühlhaus/Lebensmittellager | Ja | Kälte/Klima direkt Kernthema |
| Serverraum/Rechenzentrum | Ja | Klima nötig |
| Reiner Innenausbau ohne Hüllen-Bezug | eher nein | Gebäudehülle unverändert, kein Trigger |
| Industriehalle ohne ständigen Personenaufenthalt | eher nein | Ausser spezifische Prozessanforderung |
| Tiefbau/Strassenbau/Kanalisation | Nein | Kein Gebäude, kein Bezug |
| Fahrzeug-/Mobiliar-/IT-Beschaffung | Nein | Keine Gebäudetechnik betroffen |
| Reine Elektroinstallation (ohne Hüllensanierung) | eher nein | Nicht zwingend gekoppelt |

**HARTE REGEL (nicht verhandelbar, 2026-10-07 bestätigt):** Die Empfehlungs-
Logik/Tabelle oben ist **ausschliesslich für den Empfehlungs-Text**. Sie darf
**niemals** dazu benutzt werden, einen Treffer aus der Liste zu entfernen oder
zu verstecken. Jeder Treffer, der die harten Filter (Kanton BS/BL/AG/SO,
erlaubter PubType) besteht, **bleibt in der Liste** — egal wie niedrig der
Score (auch 3 Punkte), egal was die KI-Einschätzung zur Empfehlung sagt. Die
KI trifft keine Rauswurf-Entscheidung aufgrund von Textinhalt/eigenem
Ermessen. Sortierung ja (nach Score), Verwerfen nein.

## Mailto-Text pro Treffer — PERSONALISIERT (nicht mehr generisch!)

Wichtigste Änderung ggü. dem bisherigen generischen Text: der Mailto-Body wird
**pro Treffer individuell aus Kurzfassung+Empfehlung** generiert, nicht mehr
ein Standardtext für alle. Finale Struktur (bestätigt):

```
Guten Tag

{individueller Beobachtungssatz, NUR Lüftung/Klima-relevant, keine anderen
Gewerke erwähnen, auch nicht "nicht aber das andere"-Konstruktionen}

Falls das noch nicht vergeben ist: Wir sind auf solche Fälle spezialisiert und
würden uns gerne die Ausschreibungsunterlagen dazu ansehen, um Ihnen eine
Offerte zu erstellen.

Können Sie uns die entsprechenden Unterlagen zukommen lassen, oder ist dazu
bereits etwas direkt auf simap.ch verfügbar?

{optional, siehe Bedingung unten: "Falls Schreiben gerade keine Zeit lässt:
Geht auch telefonisch — Mittwoch 9 Uhr würde bei mir passen."}
```

KEIN "Freundliche Grüsse" am Ende (steckt schon in der Mail-Signatur).

**Bedingung für den Telefon-Satz:** nimm den Mittwoch der **nächsten**
Kalenderwoche nach dem Report-Generierungsdatum. Liegt dieser Mittwoch vor der
Eingabefrist des Treffers (mit Sicherheitspuffer, z.B. mind. 1-2 Tage davor)?
Ja → Satz einbauen. Nein (Frist zu knapp oder schon vorbei) → Satz komplett
weglassen, keine Alternative einbauen.

Beispiel-Mailtext (für #43758-01, Report-Datum 06.10., Frist 28.10., nächster
Mittwoch = 14.10., liegt klar vor Frist → Satz wird eingebaut):
```
Guten Tag

Uns ist aufgefallen, dass bei Ihrem Projekt "Sanierung Bergschule Avrona" auch
eine Lüftungserneuerung (Radonsanierung) vorgesehen ist.

Falls das noch nicht vergeben ist: Wir sind auf solche Fälle spezialisiert und
würden uns gerne die Ausschreibungsunterlagen dazu ansehen, um Ihnen eine
Offerte zu erstellen.

Können Sie uns die entsprechenden Unterlagen zukommen lassen, oder ist dazu
bereits etwas direkt auf simap.ch verfügbar? Falls Schreiben gerade keine Zeit
lässt: Geht auch telefonisch — Mittwoch 9 Uhr würde bei mir passen.
```

## Noch offen / nicht final entschieden

- Keyword-/Filterlogik: **geklärt/geschlossen (2026-10-07)** — es gibt
  bewusst KEINEN eigenen Wort-Filter, nur den Keyword-Score, der in die
  Punktzahl einfliesst, aber nichts ausfiltert
- Empfehlungs-Logik: **geklärt/geschlossen (2026-10-07)** — die Tabelle mit
  "eher Ja/eher Nein" IST die fertige Logik, nichts weiter nötig
- PubType-Begriffs-Übersetzungen: **geklärt/geschlossen (2026-10-07)** — Nutzer
  hat die offiziellen simap-Begriffe direkt gepastet (aus deren eigenem
  Publikationsart-Filter): tender→Ausschreibung, request_for_information→
  Request for Information (RFI), study_contract→Studienauftrag,
  competition→Wettbewerb, advance_notice→Vorankündigung. Alle fünf final.
- Excel wurde explizit abgelehnt ("Excel ist Handarbeit") — nicht erneut vorschlagen
- Lokales Git-Repo existiert (`/Users/damirstojadinovic/simap`, Remote
  `https://github.com/dastfaga/simap.git` gesetzt), aber **noch nicht gepusht**
  (Nutzer: "push nein") — nicht eigenmächtig pushen ohne erneute Zustimmung
- **Routine-Prompt wurde 2026-10-07 komplett überarbeitet (Schwellen 20/10 +
  volle KI-Auswertung/personalisierter Mailtext eingebaut), aber noch NICHT
  live getestet** — erster echter Testlauf ist der 08.10.2026 06:00 UTC
  Vorab-Lauf. Ergebnis/Mailformat danach prüfen (`list_runs`/`get_run_log`).
