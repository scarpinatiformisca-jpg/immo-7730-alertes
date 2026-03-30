"""Scraper Notaires.be - ventes publiques secteur 7730."""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "fr-BE,fr;q=0.9",
}

COMMUNES = ["7730", "Estaimpuis", "Leers-Nord", "Nechin", "Bailleul", "Saint-Léger", "Taintignies"]

SEARCH_URLS = [
    "https://www.notaires.be/fr/ventes-immobilieres?localite=7730",
    "https://www.notaires.be/fr/ventes-immobilieres?search=estaimpuis",
]


def get_listings():
    """Récupère les ventes publiques notariales pour le secteur 7730."""
    results = []
    seen_ids = set()

    for url in SEARCH_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  Notaires.be HTTP {resp.status_code} pour {url}")
                continue

            biens = _parse_page(resp.text, url)
            for bien in biens:
                if bien["externe_id"] not in seen_ids:
                    seen_ids.add(bien["externe_id"])
                    results.append(bien)

            print(f"  Notaires.be: {len(biens)} annonces trouvées")
            time.sleep(2)

        except Exception as e:
            print(f"  Notaires.be erreur: {e}")

    return results


def _parse_page(html, base_url):
    """Parse la page de résultats notaires.be."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Sélecteurs possibles pour les cartes de biens
    selectors = [
        ".property-card", ".sale-item", ".vente-item",
        "article", ".bien-item", "[class*='property']",
        "[class*='listing']",
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) > 1:
            break

    for card in cards:
        try:
            bien = _parse_card(card, base_url)
            if bien:
                results.append(bien)
        except Exception:
            continue

    return results


def _parse_card(card, base_url):
    """Parse une carte d'annonce notaires.be."""
    text = card.get_text(" ", strip=True)

    # Vérifier que c'est dans la zone 7730
    in_zone = any(c.lower() in text.lower() for c in COMMUNES)
    if not in_zone:
        return None

    link = card.find("a", href=True)
    if not link:
        return None

    href = link["href"]
    if not href.startswith("http"):
        href = "https://www.notaires.be" + href

    # ID depuis l'URL
    id_match = re.search(r"/(\d{4,})", href)
    ext_id = id_match.group(1) if id_match else re.sub(r"[^a-z0-9]", "", href)[-20:]

    # Prix
    prix = None
    price_match = re.search(r"(\d[\d\s]{2,})\s*€", text)
    if price_match:
        try:
            prix = float(price_match.group(1).replace(" ", "").replace("\xa0", ""))
        except Exception:
            pass

    # Surface habitable
    surface = None
    surf_match = re.search(r"(\d+)\s*m²", text)
    if surf_match:
        try:
            surface = float(surf_match.group(1))
        except Exception:
            pass

    # Titre
    titre_el = card.select_one("h2, h3, h4, strong, .title")
    titre = titre_el.get_text(strip=True) if titre_el else link.get_text(strip=True)

    # Localité
    localite = "Estaimpuis"
    for commune in COMMUNES[1:]:
        if commune.lower() in text.lower():
            localite = commune
            break

    return {
        "source": "notaires",
        "externe_id": str(ext_id),
        "url": href,
        "titre": titre or "Vente publique 7730",
        "prix": prix,
        "surface_habitable": surface,
        "surface_terrain": None,
        "localite": localite,
        "code_postal": "7730",
        "chambres": None,
        "description": text[:2000],
    }
