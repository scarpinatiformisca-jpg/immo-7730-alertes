"""Scraper Immoweb.be - secteur 7730."""

import re
import time
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-BE,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_URL = "https://www.immoweb.be/fr/recherche/maison-et-appartement/a-vendre"


def get_listings(max_price=500000, min_surface=150, postal_code="7730"):
    """Récupère toutes les annonces Immoweb correspondant aux critères."""
    results = []
    page = 1

    while True:
        params = {
            "countries": "BE",
            "postalCodes": postal_code,
            "maxPrice": max_price,
            "minNetHabitableSurface": min_surface,
            "orderBy": "newest",
            "page": page,
        }

        try:
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  Immoweb HTTP {resp.status_code} page {page}")
                break

            biens = _parse_page(resp.text)
            if not biens:
                break

            results.extend(biens)
            print(f"  Immoweb page {page}: {len(biens)} biens")

            if len(biens) < 30:
                break

            page += 1
            time.sleep(2)

        except Exception as e:
            print(f"  Immoweb erreur page {page}: {e}")
            break

    return results


def _parse_page(html):
    """Parse une page de résultats Immoweb."""
    # Tenter d'extraire le JSON embarqué dans le HTML
    match = re.search(r'window\.__INIT_DATA__\s*=\s*(\{.+?\});\s*</script>', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            biens = _from_json(data)
            if biens:
                return biens
        except Exception:
            pass

    # Fallback : parse HTML
    return _from_html(html)


def _from_json(data):
    """Extrait les annonces depuis window.__INIT_DATA__."""
    results = []
    try:
        classifieds = (
            data.get("results", {}).get("results", [])
            or data.get("classifieds", [])
        )
        for c in classifieds:
            try:
                prix = c.get("price", {}).get("mainValue") or c.get("price", {}).get("displayValue")
                surface = c.get("netHabitableSurface") or c.get("livingArea")
                terrain = c.get("landSurface") or c.get("gardenSurface")
                ext_id = str(c.get("id", ""))
                if not ext_id:
                    continue
                results.append({
                    "source": "immoweb",
                    "externe_id": ext_id,
                    "url": f"https://www.immoweb.be/fr/annonce/{ext_id}",
                    "titre": c.get("title", "") or c.get("propertyType", ""),
                    "prix": float(prix) if prix else None,
                    "surface_habitable": float(surface) if surface else None,
                    "surface_terrain": float(terrain) if terrain else None,
                    "localite": c.get("locality", "") or c.get("city", ""),
                    "code_postal": str(c.get("postalCode", "7730")),
                    "chambres": c.get("bedroom", {}).get("count") if isinstance(c.get("bedroom"), dict) else c.get("bedroomCount"),
                    "description": c.get("description", "") or "",
                })
            except Exception:
                continue
    except Exception:
        pass
    return results


def _from_html(html):
    """Fallback : parse le HTML des cartes de résultats."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    cards = soup.select("article[data-classified-id], article.card--result")
    for card in cards:
        try:
            ext_id = card.get("data-classified-id", "")
            if not ext_id:
                continue

            link = card.select_one("a[href*='/annonce/']")
            url = link["href"] if link else f"https://www.immoweb.be/fr/annonce/{ext_id}"

            # Prix
            prix = None
            for sel in ["[class*='price']", ".card__price", "[data-testid='price']"]:
                el = card.select_one(sel)
                if el:
                    m = re.search(r"[\d\s\.]+", el.get_text().replace(",", "").replace(".", "").replace("\xa0", ""))
                    if m:
                        try:
                            prix = float(m.group().replace(" ", ""))
                        except Exception:
                            pass
                    break

            # Surface habitable
            surface = None
            for el in card.select("[class*='surface'], [class*='habitable']"):
                m = re.search(r"(\d+)", el.get_text())
                if m:
                    surface = float(m.group(1))
                    break

            titre_el = card.select_one("h2, h3, [class*='title']")
            loc_el = card.select_one("[class*='locality'], [class*='location']")

            results.append({
                "source": "immoweb",
                "externe_id": str(ext_id),
                "url": url,
                "titre": titre_el.get_text(strip=True) if titre_el else "",
                "prix": prix,
                "surface_habitable": surface,
                "surface_terrain": None,
                "localite": loc_el.get_text(strip=True) if loc_el else "",
                "code_postal": "7730",
                "chambres": None,
                "description": "",
            })
        except Exception:
            continue

    return results
