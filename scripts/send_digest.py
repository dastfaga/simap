#!/usr/bin/env python3
"""
Baut aus den gescorten simap-Ergebnissen eine nach Punktzahl sortierte
Uebersicht und oeffnet sie als vorausgefuellten Mail-Entwurf (an sich selbst).
Kein Login/Versand-API noetig -- nutzt den mailto: + macOS `open` Mechanismus.
"""
import argparse
import glob
import json
import subprocess
import urllib.parse
from pathlib import Path


def load_all(pattern: str) -> list[dict]:
    entries = []
    for path in glob.glob(pattern):
        try:
            entries.extend(json.load(open(path, encoding="utf-8")))
        except Exception:
            continue
    # Duplikate (gleiche Projektnummer) raus
    seen = {}
    for e in entries:
        seen[e["projectNumber"]] = e
    return list(seen.values())


def build_body(entries: list[dict], top_n: int) -> str:
    entries = sorted(entries, key=lambda e: -e["totalScore"])[:top_n]
    lines = [f"simap.ch Wochenreport -- {len(entries)} Treffer, sortiert nach Punktzahl", ""]
    for e in entries:
        alarm = "ALARM" if e.get("alarm") else "-"
        lines.append(f"[{e['totalScore']:>2} pts | {alarm}] {e['title']}")
        lines.append(f"  Auftraggeber: {e.get('procOffice')}  |  Kanton: {e.get('canton')}")
        lines.append(f"  simap: {e['simap_url']}")
        if e.get("mailto"):
            lines.append(f"  Mail-Entwurf an Auftraggeber: {e['mailto']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="output/test_*.json")
    parser.add_argument("--to", default="damir.stojadinovic@fagaklima.ch")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    entries = load_all(args.pattern)
    if not entries:
        print("Keine Daten gefunden fuer Pattern:", args.pattern)
        return
    body = build_body(entries, args.top)
    subject = f"simap.ch Wochenreport - {len(entries)} Treffer (Test)"
    params = {"subject": subject, "body": body}
    mailto_url = f"mailto:{args.to}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

    out = Path("output/digest_preview.txt")
    out.write_text(f"Subject: {subject}\n\n{body}", encoding="utf-8")
    print(f"Vorschau gespeichert: {out}")

    subprocess.run(["open", mailto_url])
    print("Mail-Entwurf geoeffnet (Standard-Mailprogramm).")


if __name__ == "__main__":
    main()
