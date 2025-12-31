import smtplib
import json
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# ===== CHARGER .env =====
load_dotenv()

EMAIL_EXPEDITEUR = os.getenv("EMAIL_EXPEDITEUR")
MOT_DE_PASSE = os.getenv("MOT_DE_PASSE")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
DOSSIER_FICHIERS = os.getenv("DOSSIER_FICHIERS")
USERS_FILE = os.getenv("USERS_FILE")

# ===== VERIFICATION =====
if not EMAIL_EXPEDITEUR or not MOT_DE_PASSE:
    raise ValueError("❌ EMAIL_EXPEDITEUR ou MOT_DE_PASSE manquant dans .env")

# ===== LIRE USERS =====
with open(USERS_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

emails = [u["email"] for u in users if "email" in u]

# ===== LISTER FICHIERS =====
fichiers = [
    os.path.join(DOSSIER_FICHIERS, f)
    for f in os.listdir(DOSSIER_FICHIERS)
    if os.path.isfile(os.path.join(DOSSIER_FICHIERS, f))
]

if not fichiers:
    print("⚠️ Aucun fichier à envoyer")
    exit()

# ===== ENVOI =====
with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as serveur:
    serveur.login(EMAIL_EXPEDITEUR, MOT_DE_PASSE)

    for email in emails:
        msg = EmailMessage()
        msg["From"] = EMAIL_EXPEDITEUR
        msg["To"] = email
        msg["Subject"] = "Envoi automatique de fichiers"
        msg.set_content("Bonjour,\n\nVeuillez trouver les fichiers en pièce jointe.\n\nCordialement.")

        for fichier in fichiers:
            with open(fichier, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=os.path.basename(fichier)
                )

        serveur.send_message(msg)
        print(f"✅ Email envoyé à {email}")

print("🎉 Envoi terminé")
