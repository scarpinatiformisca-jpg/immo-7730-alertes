"""Script principal - Recherche immobilière automatisée secteur 7730."""

import os
from datetime import datetime

from supabase import create_client

from scrapers.immoweb import get_listings as immoweb_listings
from scrapers.immovlan import get_listings as immovlan_listings
from scrapers.notaires import get_listings as notaires_listings
from scorer import score_bien
from emailer import send_daily_alert

# Configuration via variables d'environnement (GitHub Secrets)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_TO = os.environ["EMAIL_TO"]

MAX_PRICE = 500_000
MIN_SURFACE = 150
POSTAL_CODE = "7730"


def main():
    print(f"\n{'='*50}")
    print(f"Recherche immo 7730 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- Scraping de toutes les sources ---
    all_biens = []

    print(">> Immoweb.be")
    try:
        biens = immoweb_listings(max_price=MAX_PRICE, min_surface=MIN_SURFACE, postal_code=POSTAL_CODE)
        all_biens.extend(biens)
    except Exception as e:
        print(f"   ERREUR: {e}")

    print(">> Immovlan.be")
    try:
        biens = immovlan_listings(max_price=MAX_PRICE, min_surface=MIN_SURFACE)
        all_biens.extend(biens)
    except Exception as e:
        print(f"   ERREUR: {e}")

    print(">> Notaires.be")
    try:
        biens = notaires_listings()
        all_biens.extend(biens)
    except Exception as e:
        print(f"   ERREUR: {e}")

    print(f"\nTotal scrapé : {len(all_biens)} annonces\n")

    # --- Filtrage, scoring, sauvegarde ---
    nouveaux = []

    for bien in all_biens:
        if not bien.get("externe_id") or not bien.get("source"):
            continue

        # Filtre surface minimale (si disponible)
        surf = bien.get("surface_habitable")
        if surf and surf < MIN_SURFACE:
            continue

        # Filtre prix max (si disponible)
        prix = bien.get("prix")
        if prix and prix > MAX_PRICE:
            continue

        # Déjà en base ?
        try:
            existing = supabase.table("biens").select("id").eq("source", bien["source"]).eq("externe_id", bien["externe_id"]).execute()
            if existing.data:
                continue
        except Exception as e:
            print(f"  DB check erreur: {e}")
            continue

        # Scoring
        score, score_details = score_bien(bien)
        bien["score"] = score
        bien["score_details"] = score_details

        mots = (
            score_details.get("mots_cles_potentiel", {}).get("trouves", []) +
            score_details.get("mots_cles_contexte", {}).get("trouves", [])
        )
        bien["mots_cles"] = mots

        # Sauvegarde en base
        try:
            supabase.table("biens").insert({
                "source": bien["source"],
                "externe_id": bien["externe_id"],
                "url": bien.get("url"),
                "titre": (bien.get("titre") or "")[:500],
                "prix": bien.get("prix"),
                "surface_habitable": bien.get("surface_habitable"),
                "surface_terrain": bien.get("surface_terrain"),
                "localite": bien.get("localite"),
                "code_postal": bien.get("code_postal"),
                "chambres": bien.get("chambres"),
                "description": (bien.get("description") or "")[:2000],
                "score": score,
                "score_details": score_details,
                "mots_cles": mots,
            }).execute()

            nouveaux.append(bien)
            print(f"  + NOUVEAU [{score}/100] {bien.get('titre', bien['externe_id'])[:60]}")

        except Exception as e:
            print(f"  ! Erreur insert {bien['externe_id']}: {e}")

    # --- Email ---
    print(f"\n{len(nouveaux)} nouveau(x) bien(s) trouvé(s).")

    if nouveaux:
        print("Envoi de l'email...")
        try:
            send_daily_alert(nouveaux, GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO)
        except Exception as e:
            print(f"Erreur envoi email: {e}")
    else:
        print("Pas d'email envoyé (aucun nouveau bien).")

    print("\nTerminé.")


if __name__ == "__main__":
    main()
