"""Scoring engine - potentiel marchand de bien (0-100 pts)."""

KEYWORDS_HIGH = [
    "à rénover", "a renover", "à restaurer", "a restaurer",
    "travaux", "à rafraîchir", "a rafraichir",
    "fermette", "ferme", "grange", "corps de ferme",
    "divisible", "à diviser", "a diviser",
    "permis obtenu", "permis accordé", "permis accordé",
    "dépendances", "dependances", "remise", "hangar",
    "grand terrain", "vaste terrain", "grand potentiel",
]

KEYWORDS_MED = [
    "ancien", "ancienne", "cachet", "caractère", "charme",
    "opportunité", "rare", "exceptionnel", "unique",
    "jardin", "terrain", "annexe", "atelier",
    "sous-sol", "cave", "garage", "cellier",
    "plain-pied", "de plain-pied",
]

# Prix de référence au m² pour le secteur 7730
REF_PRIX_M2 = 1800


def score_bien(bien: dict) -> tuple:
    """Score un bien immobilier de 0 à 100 pour potentiel flip/réno.
    Retourne (score, détails)."""
    details = {}
    total = 0

    # 1. Prix au m² vs marché local (max 30 pts)
    if bien.get("prix") and bien.get("surface_habitable") and bien["surface_habitable"] > 0:
        prix_m2 = bien["prix"] / bien["surface_habitable"]
        if prix_m2 < REF_PRIX_M2 * 0.55:
            pts = 30
        elif prix_m2 < REF_PRIX_M2 * 0.70:
            pts = 22
        elif prix_m2 < REF_PRIX_M2 * 0.85:
            pts = 14
        elif prix_m2 < REF_PRIX_M2:
            pts = 7
        else:
            pts = 0
        details["prix_m2"] = {"valeur": round(prix_m2), "reference": REF_PRIX_M2, "points": pts}
        total += pts

    # 2. Mots-clés à fort potentiel (max 25 pts)
    desc = ((bien.get("titre") or "") + " " + (bien.get("description") or "")).lower()
    found_high = [kw for kw in KEYWORDS_HIGH if kw in desc]
    pts_high = min(25, len(found_high) * 7)
    details["mots_cles_potentiel"] = {"trouves": found_high, "points": pts_high}
    total += pts_high

    # 3. Mots-clés contextuels (max 10 pts)
    found_med = [kw for kw in KEYWORDS_MED if kw in desc]
    pts_med = min(10, len(found_med) * 3)
    details["mots_cles_contexte"] = {"trouves": found_med, "points": pts_med}
    total += pts_med

    # 4. Superficie du terrain (max 20 pts)
    terrain = bien.get("surface_terrain") or 0
    if terrain > 2000:
        pts = 20
    elif terrain > 1000:
        pts = 14
    elif terrain > 500:
        pts = 8
    elif terrain > 200:
        pts = 4
    else:
        pts = 0
    details["terrain"] = {"surface_m2": terrain, "points": pts}
    total += pts

    # 5. Grande surface habitable (max 10 pts)
    surface = bien.get("surface_habitable") or 0
    if surface > 300:
        pts = 10
    elif surface > 250:
        pts = 7
    elif surface > 200:
        pts = 4
    else:
        pts = 0
    details["surface_habitable"] = {"m2": surface, "points": pts}
    total += pts

    # 6. Vente publique notaire = bonus opportunité (5 pts)
    if bien.get("source") == "notaires":
        details["vente_publique"] = {"points": 5}
        total += 5

    return min(total, 100), details
