import os
import smtplib
from email.message import EmailMessage
import json


SEND_ATTACHMENTS = os.getenv('SEND_ATTACHMENTS', '0')  # '0' disables attachments, '1' enables


def load_emails(users_file):
    with open(users_file, "r", encoding="utf-8") as f:
        users = json.load(f)
    return [u.get("email") for u in users if u.get("email")]


def send_files(fichiers, smtp_server, smtp_port, email_exp, password, users_file, logger=None):
    """Envoie les fichiers fournis à tous les e-mails listés dans users_file.
    Si SEND_ATTACHMENTS == '0', envoie un message court (sans pièces jointes) indiquant qu'il y a de nouveaux fichiers.
    Retourne la liste des fichiers candidats (les chemins complets) pour que le caller puisse les sauvegarder/renommer.
    """
    emails = load_emails(users_file)
    fichiers_a_envoyer = [f for f in fichiers if os.path.isfile(f) and not f.endswith('.success')]

    if not fichiers_a_envoyer:
        if logger:
            logger.info("Aucun nouveau fichier à envoyer (send_email)")
        return []

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as serveur:
            serveur.login(email_exp, password)

            for email in emails:
                msg = EmailMessage()
                msg["From"] = email_exp
                msg["To"] = email
                msg["Subject"] = "Nouvelle(s) sauvegarde(s) de fichiers"

                if SEND_ATTACHMENTS in ('1', 'true', 'True'):
                    msg.set_content("Bonjour,\n\nVeuillez trouver les nouveaux fichiers en pièce jointe.\n\nCordialement.")
                    fichiers_envoyes = []
                    for fichier in fichiers_a_envoyer:
                        try:
                            with open(fichier, "rb") as f:
                                msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=os.path.basename(fichier))
                            fichiers_envoyes.append(fichier)
                        except FileNotFoundError:
                            continue
                else:
                    # attachments disabled: send a short informational message only
                    msg.set_content("Bonjour,\n\nIl y a de nouveaux fichiers sauvegardés. Ce message est informatif uniquement.\n\nCordialement.")
                    # still report the candidate files back (full paths) so caller can backup/rename
                    fichiers_envoyes = list(fichiers_a_envoyer)

                if fichiers_envoyes:
                    serveur.send_message(msg)
                    if logger:
                        logger.info(f"Email envoyé à {email} - mode pièces jointes={'oui' if SEND_ATTACHMENTS in ('1','true','True') else 'non'}")

        if logger:
            logger.info("send_email: Envoi terminé")
        # Renvoie les fichiers qui étaient candidats (la fonction de backup/rename s'en chargera ensuite)
        return fichiers_a_envoyer

    except Exception as exc:
        if logger:
            logger.exception(f"Erreur durant l'envoi des fichiers (send_email): {exc}")
        return []


def send_notification(subject, body, smtp_server, smtp_port, email_exp, password, users_file=None, notify_email=None, logger=None):
    """Envoie un email de notification simple (sans pièces jointes).
    - notify_email: chaîne d'email(s) séparées par ',' à utiliser à la place de users_file
    - users_file: chemin vers users.json si notify_email non fourni
    """
    recipients = []
    if notify_email:
        recipients = [e.strip() for e in notify_email.split(',') if e.strip()]
    elif users_file:
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            recipients = [u.get('email') for u in users if u.get('email')]
        except Exception:
            if logger:
                logger.exception("Impossible de charger les destinataires depuis users_file pour la notification")
            return False

    if not recipients:
        if logger:
            logger.warning("Aucun destinataire pour la notification")
        return False

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as serveur:
            serveur.login(email_exp, password)
            msg = EmailMessage()
            msg['From'] = email_exp
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            msg.set_content(body)
            serveur.send_message(msg)
        if logger:
            logger.info(f"Notification envoyée: {subject} à {recipients}")
        return True
    except Exception as exc:
        if logger:
            logger.exception(f"Erreur lors de l'envoi de la notification: {exc}")
        return False