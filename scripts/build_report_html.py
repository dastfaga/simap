#!/usr/bin/env python3
"""
Baut aus den gescorten simap-Ergebnissen eine nach Punktzahl sortierte
HTML-Uebersicht (fuer den Versand ueber den Gmail-Connector).

Nur Datenaufbereitung -- der eigentliche Mailversand passiert separat
ueber den Gmail-MCP-Tool-Call (send_message), nicht in diesem Skript.
"""
import argparse
import glob
import json
import html
from pathlib import Path


def load_all(pattern: str) -> list[dict]:
    entries = []
    for path in glob.glob(pattern):
        try:
            entries.extend(json.load(open(path, encoding="utf-8")))
        except Exception:
            continue
    seen = {}
    for e in entries:
        seen[e["projectNumber"]] = e
    return list(seen.values())


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


# Farbskala Score -> Ampel. Final (2026-10-07).
# Gruen = Alarm-Schwelle (>= ALARM_THRESHOLD aus fetch_simap.py)
GREEN_FROM = 20
ORANGE_FROM = 10  # 10-19 = orange, < 10 = rot


def score_color(score: int) -> str:
    # kraeftige, dark-mode-feste Farben (nicht die hellen Pastelltoene)
    if score >= GREEN_FROM:
        return "#1a8a1a"  # gruen
    if score >= ORANGE_FROM:
        return "#b36b00"  # orange
    return "#c0392b"  # rot


def build_html(entries: list[dict], top_n: int) -> str:
    entries = sorted(entries, key=lambda e: -e["totalScore"])[:top_n]
    rows = [f"<p>{len(entries)} Treffer, sortiert nach Punktzahl.</p>"]
    rows.append(
        '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:sans-serif;font-size:13px">'
        "<tr style=\"background:#eee\">"
        "<th>Score</th><th>Titel</th><th>Auftraggeber</th><th>Kanton</th><th>Distanz</th>"
        "<th>Anfrage</th><th>simap</th></tr>"
    )
    for e in entries:
        color = score_color(e["totalScore"])
        score_cell = f'<b style="color:{color}">{e["totalScore"]}</b>'
        dist = f"{e['driveKm']} km" if e.get("driveKm") is not None else "-"
        mailto_cell = f'<a href="{e["mailto"]}">Entwurf</a>' if e.get("mailto") else "-"
        rows.append(
            "<tr>"
            f'<td align="center">{score_cell}</td>'
            f"<td>{esc(e['title'])}</td>"
            f"<td>{esc(e.get('procOffice'))}</td>"
            f'<td align="center">{esc(e.get("canton"))}</td>'
            f'<td align="center">{dist}</td>'
            f"<td>{mailto_cell}</td>"
            f'<td><a href="{esc(e["simap_url"])}">Link</a></td>'
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="output/*.json")
    parser.add_argument("--top", type=int, default=400)
    parser.add_argument("--out", default="output/report.html")
    args = parser.parse_args()

    entries = load_all(args.pattern)
    if not entries:
        print("Keine Daten gefunden fuer Pattern:", args.pattern)
        return

    body = build_html(entries, args.top)
    out = Path(args.out)
    out.write_text(body, encoding="utf-8")
    print(f"{len(entries)} Treffer verarbeitet, HTML geschrieben nach {out}")


if __name__ == "__main__":
    main()
