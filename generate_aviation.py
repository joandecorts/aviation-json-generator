"""
generate_aviation.py

Genera un aviation.json ESTRUCTURAT (JSON real)
a partir de l'API oficial NOAA Aviation Weather Center.

Aquesta versió:
✅ construeix dicts Python
✅ genera JSON vàlid
✅ compatible amb metar-taf-obs.html
"""

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

METAR_URL = "https://www.aviationweather.gov/api/data/metar"
TAF_URL   = "https://www.aviationweather.gov/api/data/taf"

PUBLISH_URL = "https://www.joandecorts.io/update_aviation.php"
PUBLISH_KEY = "pr8943p3mk902J9023N09"

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

    r = requests.post(
        f"{PUBLISH_URL}?key={PUBLISH_KEY}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    r.raise_for_status()

    print("✅ JSON estructurat publicat correctament")

if __name__ == "__main__":
    main()
