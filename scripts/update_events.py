#!/usr/bin/env python3
"""Actualiza app/src/main/assets/events.json leyendo las webs oficiales.
Solo toca los deportes 'hija', 'barca_m' y 'barca_f'. El resto se deja como está.
Si una web falla, se conservan los datos anteriores de ese deporte."""
import json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

MAD = ZoneInfo("Europe/Madrid")
EVENTS = "app/src/main/assets/events.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

# --- Hija: ficha del equipo en la web de la federación ---
DAUGHTER_URL = "https://resultadosvoleibol.isquad.es/equipo.php?id=4148&id_equipo=3017&id_superficie=1&seleccion=0"
DAUGHTER_TEAM_ID = "3017"
DAUGHTER_COMP = "3a Div. Cadet Fem · Grup E"

# --- Barça: LaLiga (la versión en-GB muestra las horas en UTC) ---
LALIGA = {
    "barca_m": "https://www.laliga.com/en-GB/clubs/fc-barcelona/next-matches",
    "barca_f": "https://www.laliga.com/en-GB/clubs/fc-barcelona-femenino/next-matches",
}
LALIGA_LINK = {
    "barca_m": "https://www.laliga.com/clubes/fc-barcelona/proximos-partidos",
    "barca_f": "https://www.laliga.com/clubes/fc-barcelona-femenino/proximos-partidos",
}
COMP_NAMES = {
    "LALIGA EA SPORTS": "LaLiga",
    "Liga F Moeve": "Liga F",
    "UEFA Champions League": "Champions League",
    "UEFA Women's Champions League": "Champions League femenina",
}
TEAM_FIX = {"A Villa": "Aston Villa", "Man City": "Manchester City"}
LOWER = {"DE", "DEL", "LA", "EL", "I", "DELS", "LES"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def dedupe(s):
    w = s.split()
    n = len(w)
    if n >= 2 and n % 2 == 0 and w[0] == w[n // 2]:
        return " ".join(w[: n // 2])
    return s


def smart_case(s):
    out = []
    for w in s.split():
        if w in LOWER:
            out.append(w.lower())
        elif len(w) <= 3:
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def daughter():
    soup = BeautifulSoup(fetch(DAUGHTER_URL), "lxml")
    out = []
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        m = re.search(r"(\d{1,2}):(\d{2})\s+(\d{2})/(\d{2})/(\d{4})", text)
        if not m or "Finalizado" in text or DAUGHTER_TEAM_ID not in str(tr):
            continue
        names = [a.get_text(" ", strip=True) for a in tr.find_all("a", href=re.compile("id_equipo="))
                 if a.get_text(strip=True)]
        if len(names) < 2:
            continue
        venue = ""
        for a in tr.find_all("a", href=re.compile("google.com/maps")):
            raw = a.get_text(" ", strip=True)
            left, _, pista = raw.partition(" - ")
            venue = smart_case(dedupe(left))
            if pista:
                venue += f" (pista {pista.replace('PISTA', '').strip()})"
            break
        h, mi, d, mo, y = map(int, m.groups())
        out.append({
            "sport": "hija",
            "title": f"{smart_case(names[0])} – {smart_case(names[1])}",
            "start": datetime(y, mo, d, h, mi, tzinfo=MAD).isoformat(),
            "comp": DAUGHTER_COMP, "venue": venue, "tv": "", "url": DAUGHTER_URL,
        })
    return out


def fix_team(x):
    x = dedupe(x.strip())
    return TEAM_FIX.get(x, x)


def laliga(sport):
    soup = BeautifulSoup(fetch(LALIGA[sport]), "lxml")
    out = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 4:
            continue
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", cells[0])
        parts = re.split(r"\s+VS\s+", cells[2], maxsplit=1)
        if not m or len(parts) != 2:
            continue
        d, mo, y = map(int, m.groups())
        t = re.search(r"(\d{1,2}):(\d{2})", cells[1])
        ev = {"sport": sport, "title": f"{fix_team(parts[0])} – {fix_team(parts[1])}"}
        if t:
            dt = datetime(y, mo, d, int(t[1]), int(t[2]), tzinfo=timezone.utc).astimezone(MAD)
        else:
            dt = datetime(y, mo, d, tzinfo=MAD)
            ev["tbc"] = True
        ev["start"] = dt.isoformat()
        ev["comp"] = COMP_NAMES.get(cells[3], cells[3])
        tv = cells[4] if len(cells) > 4 and cells[4] not in ("", "-") else ""
        ev["venue"] = ""
        ev["tv"] = tv.replace(",", ", ").replace(",  ", ", ")
        ev["url"] = LALIGA_LINK[sport]
        out.append(ev)
    return out


def merge(old, new_by_sport):
    out = [e for e in old if e["sport"] not in new_by_sport]
    for sport, new in new_by_sport.items():
        prev = {e["start"][:10]: e for e in old if e["sport"] == sport}
        for e in new:
            p = prev.get(e["start"][:10])
            if p:
                for k in ("venue", "tv"):
                    if not e.get(k) and p.get(k):
                        e[k] = p[k]
            out.append(e)
    return out


def main():
    with open(EVENTS, encoding="utf-8") as f:
        old = json.load(f)
    new = {}
    for sport, fn in (("hija", daughter), ("barca_m", lambda: laliga("barca_m")),
                      ("barca_f", lambda: laliga("barca_f"))):
        try:
            evs = fn()
            print(f"{sport}: {len(evs)} eventos")
            if evs:
                new[sport] = evs
            else:
                print(f"AVISO: {sport} sin eventos; se conservan los datos anteriores")
        except Exception as ex:
            print(f"ERROR en {sport}: {ex}")
    if not new:
        print("No se pudo leer ninguna fuente")
        sys.exit(1)
    merged = merge(old, new)
    limit = datetime.now(MAD) - timedelta(days=1)
    merged = [e for e in merged if datetime.fromisoformat(e["start"]) >= limit]
    merged.sort(key=lambda e: e["start"])
    text = "[\n" + ",\n".join("  " + json.dumps(e, ensure_ascii=False) for e in merged) + "\n]\n"
    with open(EVENTS, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"events.json: {len(merged)} eventos")


if __name__ == "__main__":
    main()
