"""
generate_aviation.py

Genera un aviation.json ESTRUCTURAT (JSON real)
a partir de l'API oficial NOAA Aviation Weather Center.

Aquesta versió:
✅ construeix dicts Python
✅ genera JSON vàlid
✅ compatible amb metar-taf-obs.html
✅ reintents NOAA/AviationWeather
✅ només publica si canvia algun issued METAR/TAF
✅ actualitza data/aviation_last.json com a cache al repo
"""

import json
import os
import requests
import time
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIGURACIÓ
# ─────────────────────────────────────────────

AIRPORTS = {
    "LEGE": "Girona – Costa Brava",
    "LEBL": "Barcelona – El Prat",
}

METAR_URL = "https://aviationweather.gov/api/data/metar"
TAF_URL   = "https://aviationweather.gov/api/data/taf"

PUBLISH_URL = "https://www.joandecorts.io/update_aviation.php"
PUBLISH_KEY = "pr8943p3mk902J9023N09"

CACHE_PATH = os.path.join("data", "aviation_last.json")

# ─────────────────────────────────────────────
# FUNCIONS AUXILIARS
# ─────────────────────────────────────────────

def get_json(url, params, retries=3, timeout=30):
    """Crida NOAA i retorna JSON.

    NOAA/AviationWeather a vegades triga a respondre. Fem alguns reintents
    abans de fallar perquè el workflow no peti per un timeout puntual.
    """
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=timeout
            )
            r.raise_for_status()

            print("STATUS:", r.status_code)
            print("CONTENT-TYPE:", r.headers.get("content-type"))
            print("URL:", r.url)
            print("BODY:", r.text[:300])

            return r.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"⚠️ Intent {attempt}/{retries} fallit per {url}: {e}")

            if attempt < retries:
                time.sleep(5 * attempt)

    raise last_error


def parse_metar(raw):
    """Converteix el METAR NOAA en un objecte senzill."""
    if not raw:
        return None

    return {
        "issued": raw.get("reportTime"),
        "raw": raw.get("rawOb"),
        "fields": {
            "category": raw.get("fltCat"),
            "visibility_m": 10000 if raw.get("visib") == "6+" else None,
            "ceiling_ft": raw.get("clds", [{}])[0].get("base") if raw.get("clds") else None,
            "wind": {
                "dir": str(raw.get("wdir")).zfill(3) if raw.get("wdir") is not None else None,
                "speed_kt": raw.get("wspd"),
                "gust_kt": None,
            },
            "temp_c": raw.get("temp"),
            "dewpoint_c": raw.get("dewp"),
            "qnh_hpa": raw.get("altim"),
        }
    }


def parse_taf(raw):
    """Converteix el TAF NOAA en objecte simple."""
    if not raw:
        return None

    return {
        "issued": raw.get("issueTime"),
        "raw": raw.get("rawTAF"),
    }


def load_cached_payload():
    """Llegeix data/aviation_last.json si existeix."""
    if not os.path.exists(CACHE_PATH):
        print(f"ℹ️ Cache no trobada: {CACHE_PATH}")
        return None

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ No puc llegir la cache {CACHE_PATH}: {e}")
        return None


def issued_signature(payload):
    """Retorna una signatura estable dels issued METAR/TAF per aeroport."""
    if not payload:
        return None

    signature = []

    for airport in payload.get("airports", []):
        icao = airport.get("icao")
        metar = airport.get("metar") or {}
        taf = airport.get("taf") or {}

        signature.append({
            "icao": icao,
            "metar_issued": metar.get("issued"),
            "taf_issued": taf.get("issued"),
        })

    return sorted(signature, key=lambda x: x.get("icao") or "")


def has_new_data(new_payload, old_payload):
    """Decideix si cal publicar comparant issued METAR/TAF."""
    new_sig = issued_signature(new_payload)
    old_sig = issued_signature(old_payload)

    if old_sig is None:
        print("✅ No hi ha signatura anterior: publico.")
        return True

    if new_sig != old_sig:
        print("✅ Detectat canvi d'issued: publico.")
        print("Anterior:", old_sig)
        print("Nou:", new_sig)
        return True

    print("⏭️ Mateixos issued METAR/TAF: no publico.")
    return False


def save_cache(payload):
    """Guarda la còpia local que després commitejarà el workflow."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ Cache actualitzada: {CACHE_PATH}")


def publish_payload(payload):
    """Publica el JSON a Nominalia via PHP receptor."""
    r = requests.post(
        f"{PUBLISH_URL}?key={PUBLISH_KEY}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    r.raise_for_status()
    print("✅ JSON estructurat publicat correctament")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    airports_out = []

    for icao, name in AIRPORTS.items():
        metar_raw = get_json(METAR_URL, {"ids": icao, "format": "json"})
        taf_raw   = get_json(TAF_URL,   {"ids": icao, "format": "json"})

        metar = parse_metar(metar_raw[0]) if metar_raw else None
        taf   = parse_taf(taf_raw[0])     if taf_raw else None

        airports_out.append({
            "icao": icao,
            "name": name,
            "metar": metar,
            "taf": taf
        })

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "airports": airports_out
    }

    cached_payload = load_cached_payload()

    if not has_new_data(payload, cached_payload):
        return

    publish_payload(payload)
    save_cache(payload)


if __name__ == "__main__":
    main()
