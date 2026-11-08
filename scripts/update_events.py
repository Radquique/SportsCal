#!/usr/bin/env python3
"""Actualiza app/src/main/assets/events.json leyendo las webs oficiales.
Toca los deportes 'hija', 'barca_m' y 'barca_f'. El resto se deja como está.
Si una web falla, se conservan los datos anteriores de ese deporte.
Las clasificaciones se calculan SIEMPRE con la tabla de hoy; si no se pueden leer
hoy, el partido se guarda sin clasificación (nunca se reutiliza una antigua)."""
import json, re, sys, unicodedata, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

MAD = ZoneInfo("Europe/Madrid")
TODAY = datetime.now(MAD).date()
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
# --- Clasificaciones de liga (solo LaLiga y Liga F; copas y Champions no llevan) ---
STAND_URL = {
    "barca_m": "https://www.laliga.com/en-GB/laliga-easports/standing",
    "barca_f": "https://www.laliga.com/en-GB/futbol-femenino/standing",
}
STAND_COMP = {"barca_m": "LaLiga", "barca_f": "Liga F"}
SEASON = "2026/27"

# --- Champions League (UEFA): la tabla se carga con JavaScript, hace falta un navegador ---
UEFA_URL = {
    "barca_m": "https://es.uefa.com/uefachampionsleague/standings/",
    "barca_f": "https://es.uefa.com/womenschampionsleague/standings/",
}
UEFA_COMP = {"barca_m": "Champions League", "barca_f": "Champions League femenina"}
UEFA_MATCHES = {"barca_m": 8, "barca_f": 6}  # partidos de la fase liga por equipo
UEFA_ALIAS = {"psg": "Paris SG", "paris saint-germain": "Paris SG", "paris saint germain": "Paris SG",
              "manchester city": "Man City", "bayern munchen": "Bayern", "bayern múnich": "Bayern",
              "inter milan": "Inter", "internazionale": "Inter"}

COMP_NAMES = {
    "LALIGA EA SPORTS": "LaLiga",
    "Liga F Moeve": "Liga F",
    "UEFA Champions League": "Champions League",
    "UEFA Women's Champions League": "Champions League femenina",
}
TEAM_FIX = {"A Villa": "Aston Villa", "Man City": "Manchester City"}
LOWER = {"DE", "DEL", "LA", "EL", "I", "DELS", "LES"}
STOP = {"fc", "cf", "de", "ud", "cd", "sd", "rcd", "ca", "c", "club", "la", "el", "del"}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


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


# ---------- clasificaciones ----------
def tokens(name):
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return frozenset(t for t in re.findall(r"[a-z0-9]+", s) if t not in STOP)


def find_team(name, rows):
    t = tokens(name)
    if not t:
        return None
    exact = [r for r in rows if tokens(r["name"]) == t]
    if len(exact) == 1:
        return exact[0]
    sub = [r for r in rows if t <= tokens(r["name"]) or tokens(r["name"]) <= t]
    return sub[0] if len(sub) == 1 else None


def standing_text(a, b, note):
    return (f"📊 Clasificación ({note})\n"
            f"{a['name']}: {a['pos']}º · {a['pts']} pts\n"
            f"{b['name']}: {b['pos']}º · {b['pts']} pts")


def date_note():
    return f"{TODAY.day} {MESES[TODAY.month - 1]}"


def check_positions(rows):
    if len(rows) < 6 or [r["pos"] for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("tabla de clasificación no válida")


def laliga_table(sport):
    soup = BeautifulSoup(fetch(STAND_URL[sport]), "lxml")
    lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
    head = next((l for l in lines if l.lower().startswith("standing")), "")
    if SEASON not in head:
        raise ValueError(f"temporada distinta de {SEASON}: {head!r}")
    md = None
    for l in lines:
        m = re.fullmatch(r"Matchday\s+(\d+)", l)
        if m:
            md = m.group(1)
            break
    i = lines.index("GD") + 1
    rows = []
    while i + 11 <= len(lines) and lines[i].isdigit() and lines[i + 3].isdigit():
        t = lines[i:i + 11]
        rows.append({"pos": int(t[0]), "name": t[2], "pts": int(t[3])})
        i += 11
    check_positions(rows)
    return rows, md


def parse_uefa(text, total):
    """Lee la tabla de la fase liga y comprueba que es coherente antes de usarla."""
    if SEASON not in text:
        raise ValueError(f"no aparece la temporada {SEASON}")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    num = r"-?\d+"
    rows, i = [], 0
    while i < len(lines) - 10:
        if lines[i].isdigit() and not re.fullmatch(num, lines[i + 1]):
            nums = lines[i + 2:i + 10]
            if all(re.fullmatch(num, n) for n in nums):
                P, W, D, L, GF, GA, GD, PTS = map(int, nums)
                if P == W + D + L and PTS == 3 * W + D and GF - GA == GD:
                    rows.append({"pos": int(lines[i]), "name": lines[i + 1], "pts": PTS, "played": P})
                    i += 10
                    continue
        i += 1
    check_positions(rows)
    if max(r["played"] for r in rows) >= total:
        raise ValueError("la fase liga ya ha terminado")
    return rows


def uefa_table(sport):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context(locale="es-ES", timezone_id="Europe/Madrid",
                                      viewport={"width": 1280, "height": 2000})
            page = ctx.new_page()
            page.goto(UEFA_URL[sport], wait_until="domcontentloaded", timeout=90000)
            for txt in ["Aceptar todas", "Aceptar", "Accept all", "Accept"]:
                try:
                    page.get_by_role("button", name=txt).first.click(timeout=2000)
                    break
                except Exception:
                    pass
            page.wait_for_function(
                "document.body.innerText.includes('Diferencia de goles') && "
                "document.body.innerText.includes('Puntos')", timeout=60000)
            page.wait_for_timeout(8000)
            text = page.inner_text("body")
        finally:
            browser.close()
    return parse_uefa(text, UEFA_MATCHES[sport])


def add_uefa_standings(sport, evs):
    targets = [e for e in evs if e["comp"] == UEFA_COMP[sport]]
    if not targets:
        return
    try:
        rows = uefa_table(sport)
    except Exception as ex:
        print(f"AVISO: sin clasificación de Champions ({sport}) hoy ({ex}); los partidos van sin ella")
        return
    n = 0
    for e in targets:
        parts = e["title"].split(" – ")
        if len(parts) != 2:
            continue
        a = find_team(UEFA_ALIAS.get(parts[0].lower(), parts[0]), rows)
        b = find_team(UEFA_ALIAS.get(parts[1].lower(), parts[1]), rows)
        if a and b:
            e["standing"] = standing_text(a, b, f"fase liga · {date_note()}")
            e["asof"] = TODAY.isoformat()
            n += 1
    print(f"{sport}: clasificación de Champions añadida a {n} partidos")


def add_league_standings(sport, evs):
    try:
        rows, md = laliga_table(sport)
    except Exception as ex:
        print(f"AVISO: sin clasificación de {sport} hoy ({ex}); los partidos van sin ella")
        return
    note = date_note() + (f" · J{md}" if md else "")
    n = 0
    for e in evs:
        if not e["comp"].startswith(STAND_COMP[sport]):
            continue  # Champions, copas...: sin clasificación
        parts = e["title"].split(" – ")
        if len(parts) != 2:
            continue
        a, b = find_team(parts[0], rows), find_team(parts[1], rows)
        if a and b:
            e["standing"] = standing_text(a, b, note)
            e["asof"] = TODAY.isoformat()
            n += 1
    print(f"{sport}: clasificación añadida a {n} partidos")


# ---------- hija ----------
def daughter_table(soup):
    table = {}
    for tr in soup.find_all("tr"):
        links = [x for x in tr.find_all("a", href=re.compile("id_equipo="))
                 if x.get_text(strip=True) and "equipo.php" not in x.get_text()]
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        ints = [int(c) for c in cells if re.fullmatch(r"\d+", c)]
        if not links or len(ints) < 8 or re.search(r"\d{2}/\d{2}/\d{4}", tr.get_text(" ")):
            continue
        m = re.search(r"id_equipo=(\d+)", links[-1]["href"])
        if m:
            table[m.group(1)] = {"name": smart_case(links[-1].get_text(" ", strip=True)),
                                 "pos": ints[0], "pts": ints[1]}
    check_positions(sorted(table.values(), key=lambda r: r["pos"]))
    return table


def daughter():
    soup = BeautifulSoup(fetch(DAUGHTER_URL), "lxml")
    try:
        table = daughter_table(soup)
    except Exception as ex:
        print(f"AVISO: sin clasificación de la hija hoy ({ex})")
        table = {}
    out = []
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2})", text)
        if not m or "finalizado" in text.lower() or DAUGHTER_TEAM_ID not in str(tr):
            continue
        links = [a for a in tr.find_all("a", href=re.compile("id_equipo=")) if a.get_text(strip=True)]
        if len(links) < 2:
            continue
        names = [a.get_text(" ", strip=True) for a in links]
        ids = [re.search(r"id_equipo=(\d+)", a["href"]).group(1) for a in links[:2]]
        venue = ""
        for a in tr.find_all("a", href="#"):
            raw = a.get_text(" ", strip=True)
            if len(raw) < 4:
                continue
            left, _, pista = raw.partition(" - ")
            venue = smart_case(dedupe(left))
            if pista:
                venue += f" (pista {pista.replace('PISTA', '').strip()})"
            break
        d, mo, y, h, mi = map(int, m.groups())
        ev = {
            "sport": "hija",
            "title": f"{smart_case(names[0])} – {smart_case(names[1])}",
            "start": datetime(y, mo, d, h, mi, tzinfo=MAD).isoformat(),
            "comp": DAUGHTER_COMP, "venue": venue, "tv": "", "url": DAUGHTER_URL,
        }
        if ids[0] in table and ids[1] in table:
            ev["standing"] = standing_text(table[ids[0]], table[ids[1]], date_note())
            ev["asof"] = TODAY.isoformat()
        out.append(ev)
    return out


# ---------- Barça ----------
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
    if out:
        add_league_standings(sport, out)
        add_uefa_standings(sport, out)
    return out


def merge(old, new_by_sport):
    out = [e for e in old if e["sport"] not in new_by_sport]
    for sport, new in new_by_sport.items():
        prev = {e["start"][:10]: e for e in old if e["sport"] == sport}
        for e in new:
            p = prev.get(e["start"][:10])
            if p:
                for k in ("venue", "tv"):  # nunca se copia la clasificación antigua
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
    # Salvaguarda: cualquier clasificación que no sea de hoy se elimina
    for e in merged:
        if e.get("asof") != TODAY.isoformat():
            e.pop("standing", None)
            e.pop("asof", None)
    limit = datetime.now(MAD) - timedelta(days=1)
    merged = [e for e in merged if datetime.fromisoformat(e["start"]) >= limit]
    merged.sort(key=lambda e: e["start"])
    text = "[\n" + ",\n".join("  " + json.dumps(e, ensure_ascii=False) for e in merged) + "\n]\n"
    with open(EVENTS, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"events.json: {len(merged)} eventos")


if __name__ == "__main__":
    main()
