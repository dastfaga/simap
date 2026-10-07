#!/usr/bin/env python3
"""
Fragt die oeffentliche simap.ch API ab, filtert Ausschreibungen, bewertet sie
per Keyword- und PubType-Score und holt pro Treffer die Auftraggeber-Kontaktdaten.

Noch ohne KI-Bewertung und ohne Office365-Versand (Weg A: mailto-Links).
"""
import argparse
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://www.simap.ch/api"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"
OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"

# Firmenstandort fagaklima.ch (fix, einmal geocodiert)
COMPANY_ADDRESS = "Helsinkistrasse 12, 4142 Muenchenstein"
COMPANY_LATLON = (47.5320424, 7.6088254)

ALARM_THRESHOLD = 20  # final (2026-10-07): identisch mit Gruen-Schwelle der Farbskala

HOME_CANTONS = {"BS", "BL"}
NEAR_KM_THRESHOLD = 50


def location_score(canton: str | None, drive_km: float | None) -> int:
    if canton in HOME_CANTONS:
        return 10
    if drive_km is not None and drive_km <= NEAR_KM_THRESHOLD:
        return 6
    return 3

_PLZ_CACHE: dict[str, tuple[float, float] | None] = {}

# PubType-Score: wie "heiss" die Phase fuer eine unaufgeforderte Anfrage ist
PUB_TYPE_SCORES = {
    "tender": 10,
    "request_for_information": 7,
    "study_contract": 3,
    "competition": 2,
    "advance_notice": 1,
}
KEPT_PUB_TYPES = list(PUB_TYPE_SCORES.keys())

# Keyword-Score: Max-Score gewinnt, kein Aufaddieren
KEYWORD_SCORES = [
    (re.compile(r"l[üu]ft", re.IGNORECASE), 10),
    (re.compile(r"klima", re.IGNORECASE), 8),
    (re.compile(r"k[äa]lte", re.IGNORECASE), 6),
    (re.compile(r"heizung", re.IGNORECASE), 4),
    (re.compile(r"haustechnik", re.IGNORECASE), 3),
    (re.compile(r"geb[äa]udetechnik", re.IGNORECASE), 3),
]


def api_get(path: str, params: dict) -> dict:
    query = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for v in value:
                query.append((key, v))
        else:
            query.append((key, value))
    url = f"{API_BASE}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_projects_all(search: str | None, cantons: list[str] | None,
                         cpv_codes: list[str] | None, pub_types: list[str] | None,
                         lang: str = "de", date_from: str | None = None,
                         date_until: str | None = None, max_pages: int = 500) -> list[dict]:
    """Vollstaendige Pagination ueber alle Treffer (rolling pagination via lastItem)."""
    results = []
    last_item = None
    for _ in range(max_pages):
        params = {
            "search": search,
            "lang": lang,
            "orderAddressCantons": cantons,
            "cpvCodes": cpv_codes,
            "newestPubTypes": pub_types,
            "newestPublicationFrom": date_from,
            "newestPublicationUntil": date_until,
            "lastItem": last_item,
        }
        data = api_get("/publications/v2/project/project-search", params)
        projects = data.get("projects", [])
        results.extend(projects)
        new_last = (data.get("pagination") or {}).get("lastItem")
        if not projects or not new_last or new_last == last_item:
            break
        last_item = new_last
    return results


def get_publication_details(project_id: str, publication_id: str) -> dict:
    return api_get(
        f"/publications/v1/project/{project_id}/publication-details/{publication_id}",
        {},
    )


def extract_contact(details: dict) -> dict:
    info = details.get("project-info", {})
    addr = info.get("procOfficeAddress") or {}
    name = (addr.get("name") or {}).get("de") or ""
    email = addr.get("email")
    phone = addr.get("phone")
    return {"name": name, "email": email, "phone": phone}


def keyword_score(details: dict) -> tuple[int, str | None]:
    """Durchsucht den gesamten Detail-Text, gibt (max_score, matched_keyword) zurueck."""
    text = json.dumps(details, ensure_ascii=False)
    best_score, best_label = 0, None
    for pattern, score in KEYWORD_SCORES:
        if score > best_score and pattern.search(text):
            best_score, best_label = score, pattern.pattern
    return best_score, best_label


def geocode_plz(plz: str) -> tuple[float, float] | None:
    """PLZ -> (lat, lon) via Nominatim (OSM), mit lokalem Cache fuer den Lauf."""
    if not plz:
        return None
    if plz in _PLZ_CACHE:
        return _PLZ_CACHE[plz]
    params = {"postalcode": plz, "country": "Switzerland", "format": "json", "limit": "1"}
    url = f"{NOMINATIM_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "simap-fetch/1.0 (fagaklima.ch)"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data:
            _PLZ_CACHE[plz] = None
            return None
        latlon = (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception:
        latlon = None
    _PLZ_CACHE[plz] = latlon
    time.sleep(1)  # Nominatim Fair-Use: max 1 req/s
    return latlon


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def driving_distance_km(target: tuple[float, float]) -> tuple[float, float] | None:
    """Gibt (km, minuten) via OSRM zurueck, oder None bei Fehler."""
    lat1, lon1 = COMPANY_LATLON
    lat2, lon2 = target
    url = f"{OSRM_BASE}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    req = urllib.request.Request(url, headers={"User-Agent": "simap-fetch/1.0 (fagaklima.ch)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        route = data["routes"][0]
        return round(route["distance"] / 1000, 1), round(route["duration"] / 60, 1)
    except Exception:
        return None


def estimate_distance_km(plz: str, canton: str | None, drive: bool = False) -> dict:
    empty = {"distanceKm": None, "driveKm": None, "driveMinutes": None}
    if canton in HOME_CANTONS:
        return empty  # BS/BL: Kanton reicht fuer den Score, keine Maps-Abfrage noetig
    target = geocode_plz(plz)
    if not target:
        return empty
    result = {"distanceKm": round(haversine_km(COMPANY_LATLON, target), 1),
              "driveKm": None, "driveMinutes": None}
    if drive:
        driving = driving_distance_km(target)
        if driving:
            result["driveKm"], result["driveMinutes"] = driving
    return result


def build_mailto(to_email: str, subject: str, body: str) -> str:
    params = {"subject": subject, "body": body}
    return f"mailto:{to_email}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


def main():
    parser = argparse.ArgumentParser(description="simap.ch Ausschreibungen abfragen und scoren")
    parser.add_argument("--search", default=None, help="Suchbegriff (min. 3 Zeichen)")
    parser.add_argument("--cantons", nargs="*", default=None, help="z.B. BS BL AG SO")
    parser.add_argument("--cpv", nargs="*", default=None, help="CPV-Codes")
    parser.add_argument("--pub-types", nargs="*", default=KEPT_PUB_TYPES,
                         help=f"Standard: {KEPT_PUB_TYPES}")
    parser.add_argument("--date-from", default=None, help="juengste Publikation ab YYYY-MM-DD")
    parser.add_argument("--date-until", default=None, help="juengste Publikation bis YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None,
                         help="max. Anzahl Treffer mit Detailabfrage (Default: alle)")
    parser.add_argument("--out", default="output/simap_results.json")
    parser.add_argument("--drive", action="store_true",
                         help="zusaetzlich echte Fahrdistanz/-zeit via OSRM berechnen (langsamer)")
    args = parser.parse_args()

    if not args.search and not args.cantons and not args.cpv:
        print("Fehler: mindestens --search oder ein Filter (--cantons/--cpv) angeben.", file=sys.stderr)
        sys.exit(1)

    projects = search_projects_all(args.search, args.cantons, args.cpv, args.pub_types,
                                    date_from=args.date_from, date_until=args.date_until)
    todo = projects if args.limit is None else projects[: args.limit]
    print(f"{len(projects)} Projekte gefunden, hole Details zu {len(todo)}...")

    enriched = []
    for i, p in enumerate(todo, 1):
        try:
            details = get_publication_details(p["id"], p["publicationId"])
        except Exception as e:
            print(f"  [{i}/{len(todo)}] Fehler bei {p.get('projectNumber')}: {e}", file=sys.stderr)
            continue
        contact = extract_contact(details)
        kw_score, kw_match = keyword_score(details)
        pub_score = PUB_TYPE_SCORES.get(p.get("pubType"), 0)
        title = (p.get("title") or {}).get("de") or ""
        order_addr = p.get("orderAddress") or {}
        plz = order_addr.get("postalCode")
        canton = order_addr.get("cantonId")
        dist = estimate_distance_km(plz, canton, drive=args.drive)
        loc_score = location_score(canton, dist.get("driveKm"))
        total_score = pub_score + kw_score + loc_score
        entry = {
            "projectNumber": p.get("projectNumber"),
            "title": title,
            "pubType": p.get("pubType"),
            "pubTypeScore": pub_score,
            "keywordScore": kw_score,
            "keywordMatch": kw_match,
            "locationScore": loc_score,
            "totalScore": total_score,
            "alarm": total_score >= ALARM_THRESHOLD,
            "canton": canton,
            **dist,
            "publicationDate": p.get("publicationDate"),
            "procOffice": (p.get("procOfficeName") or {}).get("de"),
            "contact": contact,
            "simap_url": f"https://www.simap.ch/de/project-detail/{p['id']}",
        }
        if contact.get("email"):
            subject = f"Anfrage zu Ausschreibung {entry['projectNumber']}: {title}"
            body = (
                f"Guten Tag\n\n"
                f"Wir interessieren uns fuer Ihre Ausschreibung \"{title}\" "
                f"(Projekt-Nr. {entry['projectNumber']}).\n\n"
                f"Freundliche Gruesse"
            )
            entry["mailto"] = build_mailto(contact["email"], subject, body)
        enriched.append(entry)
        if i % 25 == 0:
            print(f"  ... {i}/{len(todo)}")
        time.sleep(0.05)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Geschrieben nach {out_path}")


if __name__ == "__main__":
    main()
