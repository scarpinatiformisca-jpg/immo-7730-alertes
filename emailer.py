"""Envoi des alertes email quotidiennes."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_daily_alert(biens: list, gmail_user: str, gmail_app_password: str, email_to: str):
    """Envoie l'email d'alerte avec les nouveaux biens."""
    if not biens:
        return

    count = len(biens)
    subject = f"[Immo 7730] {count} nouveau{'x' if count > 1 else ''} bien{'s' if count > 1 else ''} - {datetime.now().strftime('%d/%m/%Y')}"

    html = _build_html(biens)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = email_to
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, email_to, msg.as_string())

    print(f"Email envoyé : {count} bien(s) à {email_to}")


def _build_html(biens: list) -> str:
    biens_sorted = sorted(biens, key=lambda b: b.get("score", 0), reverse=True)

    cards_html = ""
    for bien in biens_sorted:
        score = bien.get("score", 0)
        if score >= 60:
            color = "#27ae60"
            label = "FORT POTENTIEL"
        elif score >= 35:
            color = "#f39c12"
            label = "POTENTIEL MOYEN"
        else:
            color = "#95a5a6"
            label = "À SURVEILLER"

        prix_str = "N/A"
        prix_m2_str = ""
        if bien.get("prix"):
            prix_str = f"{int(bien['prix']):,}".replace(",", " ") + " €"
            if bien.get("surface_habitable") and bien["surface_habitable"] > 0:
                prix_m2 = int(bien["prix"] / bien["surface_habitable"])
                prix_m2_str = f" <small style='color:#888'>({prix_m2} €/m²)</small>"

        surface_str = f"{int(bien['surface_habitable'])} m²" if bien.get("surface_habitable") else "N/A"
        terrain_str = f"{int(bien['surface_terrain'])} m²" if bien.get("surface_terrain") else "N/A"
        chambres_str = str(bien["chambres"]) if bien.get("chambres") else "N/A"

        details = bien.get("score_details", {})
        mots_potentiel = details.get("mots_cles_potentiel", {}).get("trouves", [])
        mots_contexte = details.get("mots_cles_contexte", {}).get("trouves", [])
        tous_mots = mots_potentiel + mots_contexte
        mots_str = ", ".join(tous_mots) if tous_mots else "aucun"

        score_breakdown = []
        if details.get("prix_m2"):
            d = details["prix_m2"]
            score_breakdown.append(f"Prix/m²: {d['valeur']}€ vs {d['reference']}€ ref → +{d['points']}pts")
        if details.get("terrain", {}).get("points", 0) > 0:
            d = details["terrain"]
            score_breakdown.append(f"Terrain {d['surface_m2']}m² → +{d['points']}pts")
        if details.get("mots_cles_potentiel", {}).get("points", 0) > 0:
            d = details["mots_cles_potentiel"]
            score_breakdown.append(f"Mots-clés potentiel → +{d['points']}pts")
        if details.get("vente_publique"):
            score_breakdown.append("Vente publique notaire → +5pts")

        breakdown_html = "<br>".join(score_breakdown) if score_breakdown else ""

        source_badge = {
            "immoweb": "#2980b9",
            "notaires": "#8e44ad",
            "immovlan": "#16a085",
        }.get(bien.get("source", ""), "#7f8c8d")

        cards_html += f"""
        <div style="border:1px solid #ddd; border-radius:8px; margin:16px 0; overflow:hidden;
                    box-shadow:0 2px 4px rgba(0,0,0,0.08);">
          <div style="background:{color}; padding:10px 16px; display:flex; justify-content:space-between; align-items:center;">
            <span style="color:white; font-weight:bold; font-size:14px;">{label}</span>
            <span style="color:white; font-size:24px; font-weight:bold;">{score}/100</span>
          </div>
          <div style="padding:16px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
              <span style="background:{source_badge}; color:white; padding:2px 8px; border-radius:12px;
                           font-size:11px; font-weight:bold;">{(bien.get('source') or '').upper()}</span>
              <h3 style="margin:0; color:#2c3e50; font-size:16px;">{bien.get('titre') or 'Sans titre'}</h3>
            </div>

            <table style="width:100%; border-collapse:collapse; margin:10px 0;">
              <tr>
                <td style="padding:4px 8px; background:#f8f9fa; border-radius:4px; width:25%;">
                  <strong>Prix</strong>
                </td>
                <td style="padding:4px 8px;">{prix_str}{prix_m2_str}</td>
                <td style="padding:4px 8px; background:#f8f9fa; border-radius:4px; width:25%;">
                  <strong>Surface hab.</strong>
                </td>
                <td style="padding:4px 8px;">{surface_str}</td>
              </tr>
              <tr>
                <td style="padding:4px 8px; background:#f8f9fa; border-radius:4px;">
                  <strong>Terrain</strong>
                </td>
                <td style="padding:4px 8px;">{terrain_str}</td>
                <td style="padding:4px 8px; background:#f8f9fa; border-radius:4px;">
                  <strong>Chambres</strong>
                </td>
                <td style="padding:4px 8px;">{chambres_str}</td>
              </tr>
              <tr>
                <td style="padding:4px 8px; background:#f8f9fa; border-radius:4px;">
                  <strong>Localité</strong>
                </td>
                <td colspan="3" style="padding:4px 8px;">{bien.get('localite') or ''} {bien.get('code_postal') or ''}</td>
              </tr>
            </table>

            <div style="background:#fff9e6; border:1px solid #f39c12; border-radius:4px;
                        padding:8px 12px; margin:8px 0; font-size:13px;">
              <strong>Mots-clés détectés :</strong> {mots_str}
            </div>

            {"<div style='font-size:12px; color:#666; margin:6px 0;'>" + breakdown_html + "</div>" if breakdown_html else ""}

            <a href="{bien.get('url') or '#'}"
               style="display:inline-block; margin-top:10px; background:#3498db; color:white;
                      padding:8px 18px; text-decoration:none; border-radius:5px; font-size:14px;">
              Voir l'annonce →
            </a>
          </div>
        </div>
        """

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif; max-width:700px; margin:0 auto; padding:20px; color:#333;">
      <div style="background:#2c3e50; color:white; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h1 style="margin:0; font-size:22px;">Alerte Immobilière - Secteur 7730</h1>
        <p style="margin:6px 0 0; opacity:0.8;">{datetime.now().strftime('%A %d %B %Y')} — {len(biens_sorted)} nouveau(x) bien(s)</p>
      </div>
      <p style="color:#666; font-size:13px;">Triés par score de potentiel (marchand de bien). Score basé sur : prix/m², terrain, mots-clés, source.</p>
      {cards_html}
      <div style="margin-top:30px; padding-top:15px; border-top:1px solid #eee; font-size:11px; color:#aaa;">
        Alerte automatique - Recherche immo 7730 | GitHub Actions
      </div>
    </body>
    </html>
    """
