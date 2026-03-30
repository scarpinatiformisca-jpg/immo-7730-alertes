"""Scraper Immovlan.be - secteur 7730."""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

SEARCH_URL = "https://immovlan.be/fr/immobilier?transactionType=sale&postalCode=7730&minSurface={min_surface}&maxPrice={max_price}"


def get_listings(max_price=500000, min_surface=150):
    """Récupère les annonces Immovlan pour le secteur 7730."""
    results = []
    url = SEARCH_URL.format(min_surface=min_surface, max_price=max_price)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  Immovlan HTTP {resp.status_code}")
            return results

        biens = _parse_page(resp.text)
        print(f"  Immovlan: {len(biens)} annonces trouvées")
        results.extend(biens)

    except Exception as e:
        print(f"  Immovlan erreur: {e}")

    return results


def _parse_page(html):
    """Parse les résultats Immovlan."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    cards = soup.select("[data-id], .property-item, article.property, .listing-item")

    for card in cards:
        try:
            bien = _parse_card(card)
            if bien:
                results.append(bien)
        except Exception:
            continue

    return results


def _parse_card(card):
    """Parse une carte Immovlan."""
    ext_id = card.get("data-id") or card.get("id", "")
    if not ext_id:
        link = card.find("a", href=re.compile(r"/\d+"))
        if link:
            m = re.search(r"/(\d+)", link["href"])
            ext_id = m.group(1) if m else ""

    if not ext_id:
        return None

    link = card.find("a", href=True)
    url = link["href"] if link else ""
    if url and not url.startswith("http"):
        url = "https://immovlan.be" + url

    # Prix
    prix = None
    price_el = card.select_one("[class*='price']")
    if price_el:
        m = re.search(r"(\d[\d\s]+)", price_el.get_text().replace(".", "").replace(",", ""))
        if m:
            try:
                prix = float(m.group(1).replace(" ", "").replace("\xa0", ""))
            except Exception:
                pass

    # Surface
    surface = None
    for el in card.select("[class*='surface'], [class*='area']"):
        m = re.search(r"(\d+)", el.get_text())
        if m:
            surface = float(m.group(1))
            break

    titre_el = card.select_one("h2, h3, .title, [class*='title']")

    return {
        "source": "immovlan",
        "externe_id": str(ext_id),
        "url": url,
        "titre": titre_el.get_text(strip=True) if titre_el else "",
        "prix": prix,
        "surface_habitable": surface,
        "surface_terrain": None,
        "localite": "Estaimpuis",
        "code_postal": "7730",
        "chambres": None,
        "description": "",
    }
