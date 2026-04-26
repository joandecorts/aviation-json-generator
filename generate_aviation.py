"""
generate_aviation.py

Generador de JSON d'aviació (METAR + TAF)
- Fonts: NOAA Aviation Weather Center (JSON oficial)
- Aeroports inicials: LEGE, LEBL
- Resultat: POST a joandecorts.io/update_aviation.php

👉 Per afegir aeroports:
    Afegeix el codi ICAO a la llista AIRPORTS
"""

import requests
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIGURACIÓ
# ─────────────────────────────────────────────

AIRPORTS = {
    "LEGE": "Girona – Costa Brava",
    "LEBL": "Barcelona – El Prat",
}

# Endpoints NOAA (JSON)
METAR_URL = "https://www.aviationweather.gov/api/data/metar"
TAF_URL   = "https://www.aviationweather.gov/api/data/taf"

# Endpoint receptor (la teva web)
PUBLISH_URL = "https://www.joandecorts.io/update_aviation.php"
PUBLISH_KEY = "pr8943p3mk902J9023N09"  # ← la mateixa clau que ja tens

# ─────────────────────────────────────────────
# FUNCIONS
# ─────────────────────────────────────────────

def fetch_metar(icao):
    r = requests.get(
        METAR_URL,
        params={"ids": icao, "format": "json"},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None

def fetch_taf(icao):
    r = requests.get(
        TAF_URL,
        params={"ids": icao, "format": "json"},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    airports_output = []

    for icao, name in AIRPORTS.items():
        metar = fetch_metar(icao)
        taf   = fetch_taf(icao)

        airports_output.append({
            "icao": icao,
            "name": name,
            "metar": metar,
            "taf": taf
        })

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "airports": airports_output
    }

    # Publica el JSON a la teva web
    r = requests.post(
        f"{PUBLISH_URL}?key={PUBLISH_KEY}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    r.raise_for_status()

    print("JSON publicat correctament")

if __name__ == "__main__":
    main()
