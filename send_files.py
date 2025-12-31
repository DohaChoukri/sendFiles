import smtplib
import json
import os
import time
import shutil
import logging
from logging.handlers import RotatingFileHandler
from email.message import EmailMessage
from dotenv import load_dotenv

# ===== CHARGER .env =====
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EMAIL_EXPEDITEUR = os.getenv("EMAIL_EXPEDITEUR")
MOT_DE_PASSE = os.getenv("MOT_DE_PASSE")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None
DOSSIER_FICHIERS = os.getenv("DOSSIER_FICHIERS", os.path.join(BASE_DIR, "files"))
USERS_FILE = os.getenv("USERS_FILE", os.path.join(BASE_DIR, "users.json"))
DOSSIER_SAUVEGARDE = os.getenv("DOSSIER_SAUVEGARDE", r"D:\souvgarde")
# ----- Extensions autorisées -----
EXTENSIONS_FILE = os.getenv("EXTENSIONS_FILE", os.path.join(BASE_DIR, "extension.json"))

# normalize to absolute path
if not os.path.isabs(DOSSIER_SAUVEGARDE):
    DOSSIER_SAUVEGARDE = os.path.join(BASE_DIR, DOSSIER_SAUVEGARDE)
# Notifications: adresse(s) (comma-separated) ou users.json, et options
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")  # ex: "ops@example.com,admin@example.com"
NOTIFY_ON_SUCCESS = os.getenv("NOTIFY_ON_SUCCESS", "0")  # '1' to enable
NOTIFY_ON_ERROR = os.getenv("NOTIFY_ON_ERROR", "1")  # default enabled
# ===== VERIFICATIONS =====
if not EMAIL_EXPEDITEUR or not MOT_DE_PASSE:
    raise ValueError("EMAIL_EXPEDITEUR ou MOT_DE_PASSE manquant dans .env")

if SMTP_PORT is None:
    raise ValueError("SMTP_PORT manquant dans .env")

# ----- Logging -----
LOG_FILE = os.getenv("LOG_FILE", "error.log")
logger = logging.getLogger("send_files")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

LOG_FILE = os.getenv("LOG_FILE", os.path.join(BASE_DIR, "error.log"))
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)



# Startup diagnostics
logger.info(f"Script démarré. BASE_DIR={BASE_DIR} CWD={os.getcwd()}")
logger.info(f"DOSSIER_FICHIERS={DOSSIER_FICHIERS}, USERS_FILE={USERS_FILE}, LOG_FILE={LOG_FILE}")
try:
    os.makedirs(DOSSIER_FICHIERS, exist_ok=True)
    logger.info(f"Dossier de fichiers vérifié/créé: {DOSSIER_FICHIERS}")
except Exception as e:
    logger.exception(f"Impossible de créer/le vérifier le dossier {DOSSIER_FICHIERS}: {e}")

# ensure backup folder exists
try:
    os.makedirs(DOSSIER_SAUVEGARDE, exist_ok=True)
    logger.info(f"Dossier de sauvegarde vérifié/créé: {DOSSIER_SAUVEGARDE}")
except Exception as e:
    logger.exception(f"Impossible de créer/le vérifier le dossier de sauvegarde {DOSSIER_SAUVEGARDE}: {e}")

# --- Process existing .success automatically at startup
try:
    from backup import process_success_files, ensure_backup_dir
    ensure_backup_dir(DOSSIER_SAUVEGARDE, logger=logger)
    copied, removed = process_success_files(DOSSIER_FICHIERS, DOSSIER_SAUVEGARDE, logger=logger)
    if copied or removed:
        logger.info(f"Startup process-success: copiés={len(copied)}, supprimés={len(removed)}")
except Exception as e:
    logger.exception(f"Erreur lors du traitement automatique des fichiers .success au démarrage: {e}")

def show_log(lines=100):
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.readlines()
        for line in content[-lines:]:
            print(line.rstrip())
    except FileNotFoundError:
        print(f"No log file found: {LOG_FILE}")

# ----- Fonctions réutilisables -----

def load_emails():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    return [u["email"] for u in users if "email" in u]


def list_files():
    if not os.path.isdir(DOSSIER_FICHIERS):
        return []
    return [
        os.path.join(DOSSIER_FICHIERS, f)
        for f in os.listdir(DOSSIER_FICHIERS)
        if os.path.isfile(os.path.join(DOSSIER_FICHIERS, f))
    ]


def send_and_backup():
    """
    Orchestration :
    - vérifie l’extension des fichiers
    - envoie uniquement les extensions autorisées
    - sauvegarde les fichiers envoyés
    - marque les fichiers traités en .success
    - supprime les fichiers non autorisés
    """
    try:
        fichiers = [f for f in list_files() if not f.endswith('.success')]

        if not fichiers:
            logger.info("Aucun nouveau fichier à traiter")
            return False

        from send_email import send_files as do_send
        from backup import copy_files_to_backup, cleanup_success_in_source, ensure_backup_dir

        ensure_backup_dir(DOSSIER_SAUVEGARDE, logger=logger)

        fichiers_valides = []
        fichiers_invalides = []

        # 🔍 Vérification des extensions
        for fichier in fichiers:
            ext = os.path.splitext(fichier)[1].lower()
            with open(EXTENSIONS_FILE, "r", encoding="utf-8") as f:
                extensions = json.load(f)
            for ex in extensions["ext"]:
                if ex in ext:
                    fichiers_valides.append(fichier)
                else:
                    fichiers_invalides.append(fichier)

        # 🚫 Traitement des fichiers NON autorisés
        for fichier in fichiers_invalides:
            try:
                logger.warning(f"Extension non autorisée : {fichier}")
            except Exception as e:
                logger.error(f"Erreur traitement fichier non autorisé {fichier}: {e}")

        # 📤 Envoi uniquement des fichiers valides
        if not fichiers_valides:
            logger.info("Aucun fichier avec extension autorisée à envoyer")
            return False

        fichiers_envoyes = do_send(
            fichiers_valides,
            SMTP_SERVER,
            SMTP_PORT,
            EMAIL_EXPEDITEUR,
            MOT_DE_PASSE,
            USERS_FILE,
            logger=logger
        )

        if not fichiers_envoyes:
            logger.info("Aucun fichier valide n'a été envoyé")
            return False

        # 💾 Sauvegarde + renommage .success
        copy_files_to_backup(fichiers_envoyes, DOSSIER_SAUVEGARDE, logger=logger)

        for fichier in fichiers_envoyes:
            try:
                target = fichier + ".success"
                os.replace(fichier, target)
                logger.info(f"Fichier envoyé et marqué success: {fichier}")
            except Exception as e:
                logger.error(f"Erreur renommage {fichier}: {e}")

        cleanup_success_in_source(DOSSIER_FICHIERS, logger=logger)

        logger.info("send_and_backup: traitement terminé avec succès")

        # 📧 Notification succès
        if NOTIFY_ON_SUCCESS in ('1', 'true', 'True'):
            from send_email import send_notification
            send_notification(
                subject="Sauvegarde réussie",
                body="Les fichiers autorisés ont été envoyés et sauvegardés avec succès.",
                smtp_server=SMTP_SERVER,
                smtp_port=SMTP_PORT,
                email_exp=EMAIL_EXPEDITEUR,
                password=MOT_DE_PASSE,
                users_file=USERS_FILE,
                notify_email=NOTIFY_EMAIL,
                logger=logger,
            )

        return True

    except Exception as exc:
        logger.exception(f"Erreur durant send_and_backup: {exc}")

        # 📧 Notification erreur
        if NOTIFY_ON_ERROR in ('1', 'true', 'True'):
            from send_email import send_notification
            send_notification(
                subject="Erreur de sauvegarde",
                body="Une erreur est survenue lors du traitement des fichiers. Vérifiez les logs.",
                smtp_server=SMTP_SERVER,
                smtp_port=SMTP_PORT,
                email_exp=EMAIL_EXPEDITEUR,
                password=MOT_DE_PASSE,
                users_file=USERS_FILE,
                notify_email=NOTIFY_EMAIL,
                logger=logger,
            )

        return False

# ----- Envoi depuis dossier de sauvegarde (nouveau comportement demandé) -----
def send_from_backup():
    """Envoie les nouveaux fichiers présents dans DOSSIER_SAUVEGARDE et supprime après envoi."""
    try:
        # lister fichiers dans dossier sauvegarde, ignorer fichiers temporaires et déjà traités (*.sent)
        files = [os.path.join(DOSSIER_SAUVEGARDE, f) for f in os.listdir(DOSSIER_SAUVEGARDE) if os.path.isfile(os.path.join(DOSSIER_SAUVEGARDE, f)) and not f.endswith('.sent') and not f.endswith('~') and not f.startswith('~')]
        if not files:
            logger.info("Aucun nouveau fichier dans le dossier de sauvegarde à envoyer")
            return False

        from send_email import send_files as do_send

        # envoyer les fichiers trouvés
        sent = do_send(files, SMTP_SERVER, SMTP_PORT, EMAIL_EXPEDITEUR, MOT_DE_PASSE, USERS_FILE, logger=logger)

        if not sent:
            logger.info("Aucun envoi depuis la sauvegarde (aucun fichier envoyé)")
            return False

        # marquer comme envoyés et supprimer
        for f in sent:
            try:
                target = f + '.sent'
                try:
                    os.replace(f, target)
                    logger.info(f"Marqué envoyé (temp): {f} → {target}")
                except Exception:
                    if os.path.exists(target):
                        try:
                            os.remove(target)
                            os.rename(f, target)
                            logger.info(f"Marqué envoyé après suppression cible: {f} → {target}")
                        except Exception as e2:
                            logger.error(f"Erreur marquage envoyé {f}: {e2}")
                    else:
                        logger.error(f"Erreur marquage envoyé {f}")

                # supprimer le fichier .sent pour libérer l'espace (comportement demandé)
                try:
                    os.remove(target)
                    logger.info(f"Supprimé du dossier sauvegarde après envoi: {target}")
                except Exception as e:
                    logger.error(f"Impossible de supprimer {target}: {e}")
            except Exception as e:
                logger.exception(f"Erreur post-envoi sur fichier {f}: {e}")

        logger.info("send_from_backup: traitement terminé")

        # notification de succès pour envoi depuis sauvegarde
        try:
            if NOTIFY_ON_SUCCESS in ('1', 'true', 'True'):
                from send_email import send_notification
                send_notification(
                    subject="Envoi depuis sauvegarde réussi",
                    body="Les fichiers présents dans la sauvegarde ont été envoyés avec succès.",
                    smtp_server=SMTP_SERVER,
                    smtp_port=SMTP_PORT,
                    email_exp=EMAIL_EXPEDITEUR,
                    password=MOT_DE_PASSE,
                    users_file=USERS_FILE,
                    notify_email=NOTIFY_EMAIL,
                    logger=logger,
                )
        except Exception:
            logger.exception("Erreur lors de l'envoi de la notification de succès depuis sauvegarde")

        return True

    except Exception as exc:
        logger.exception(f"Erreur durant send_from_backup: {exc}")
        # notification d'erreur
        try:
            if NOTIFY_ON_ERROR in ('1', 'true', 'True'):
                from send_email import send_notification
                send_notification(
                    subject="Erreur lors de l'envoi depuis sauvegarde",
                    body="Une erreur est survenue lors de l'envoi depuis la sauvegarde. Vérifiez les logs.",
                    smtp_server=SMTP_SERVER,
                    smtp_port=SMTP_PORT,
                    email_exp=EMAIL_EXPEDITEUR,
                    password=MOT_DE_PASSE,
                    users_file=USERS_FILE,
                    notify_email=NOTIFY_EMAIL,
                    logger=logger,
                )
        except Exception:
            logger.exception("Erreur lors de l'envoi de la notification d'erreur depuis sauvegarde")

        return False


# ----- Mode watch (optionnel) -----

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:
    Observer = None
    FileSystemEventHandler = object


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, delay=1.0):
        self.delay = delay

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(self.delay)
        if event.src_path.endswith('.success') or event.src_path.endswith('~'):
            return
        logger.info(f"Nouveau fichier détecté: {event.src_path}")
        try:
            # appeler la nouvelle routine qui fait l'envoi + sauvegarde + nettoyage
            send_and_backup()
        except Exception as exc:
            logger.exception(f"Erreur dans on_created pour {event.src_path}: {exc}")


class NewBackupHandler(FileSystemEventHandler):
    def __init__(self, delay=1.0):
        self.delay = delay

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(self.delay)
        # ne pas traiter les fichiers temporaires
        name = os.path.basename(event.src_path)
        if name.endswith('.sent') or name.endswith('~') or name.startswith('~'):
            return
        logger.info(f"Nouveau fichier dans la sauvegarde détecté: {event.src_path}")
        try:
            # envoyer depuis le dossier de sauvegarde
            send_from_backup()
        except Exception as exc:
            logger.exception(f"Erreur dans on_created backup pour {event.src_path}: {exc}")


def watch_folder(poll_interval=1):
    if Observer is None:
        raise RuntimeError("Le paquet 'watchdog' n'est pas installé. Installez-le: pip install watchdog")

    # interval (s) pour traiter les fichiers existants *.success automatiquement
    PROCESS_SUCCESS_INTERVAL = int(os.getenv("PROCESS_SUCCESS_INTERVAL", "60"))

    event_handler = NewFileHandler()
    observer = Observer()
    # ensure folder exists before scheduling (useful when started by Task Scheduler)
    try:
        os.makedirs(DOSSIER_FICHIERS, exist_ok=True)
        logger.info(f"Dossier de surveillance prêt: {DOSSIER_FICHIERS}")
    except Exception as e:
        logger.exception(f"Impossible de créer/le vérifier le dossier {DOSSIER_FICHIERS}: {e}")
    observer.schedule(event_handler, DOSSIER_FICHIERS, recursive=False)
    observer.start()
    logger.info(f"Surveillance du dossier {DOSSIER_FICHIERS}. Ctrl+C pour arrêter.")

    # also start a watcher on the backup folder if requested by env var WATCH_BACKUP
    if os.getenv('WATCH_BACKUP', '0') in ('1', 'true', 'True'):
        try:
            backup_handler = NewBackupHandler()
            observer.schedule(backup_handler, DOSSIER_SAUVEGARDE, recursive=False)
            logger.info(f"Surveillance du dossier de sauvegarde {DOSSIER_SAUVEGARDE} activée")
        except Exception as e:
            logger.exception(f"Impossible d'activer le watcher sur la sauvegarde: {e}")

    # loop avec traitement périodique des fichiers .success
    last_process = 0
    try:
        while True:
            try:
                time.sleep(poll_interval)
                now = time.time()
                if now - last_process >= PROCESS_SUCCESS_INTERVAL:
                    try:
                        from backup import process_success_files, ensure_backup_dir
                        ensure_backup_dir(DOSSIER_SAUVEGARDE, logger=logger)
                        copied, removed = process_success_files(DOSSIER_FICHIERS, DOSSIER_SAUVEGARDE, logger=logger)
                        if copied or removed:
                            logger.info(f"Periodic process-success: copiés={len(copied)}, supprimés={len(removed)}")
                    except Exception as e:
                        logger.exception(f"Erreur périodique de traitement des .success: {e}")
                    last_process = now
            except Exception as exc:
                logger.exception(f"Erreur dans la boucle de surveillance: {exc}")
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ----- CLI -----
import argparse

def main():
    parser = argparse.ArgumentParser(description="Envoyer automatiquement les nouveaux fichiers")
    parser.add_argument('--watch', action='store_true', help='Surveiller le dossier et envoyer automatiquement')
    parser.add_argument('--show-log', nargs='?', const=100, type=int, help='Afficher les dernières lignes du fichier de log (optionnel: nombre de lignes)')
    parser.add_argument('--process-success', action='store_true', help="Traiter les fichiers *.success existants : copier vers sauvegarde puis supprimer")
    args = parser.parse_args()

    if args.show_log is not None:
        show_log(args.show_log)
        return

    if args.process_success:
        from backup import process_success_files, ensure_backup_dir
        ensure_backup_dir(DOSSIER_SAUVEGARDE, logger=logger)
        copied, removed = process_success_files(DOSSIER_FICHIERS, DOSSIER_SAUVEGARDE, logger=logger)
        logger.info(f"process-success: copiés={len(copied)}, supprimés={len(removed)}")
        return

    if args.watch:
        try:
            watch_folder()
        except Exception as exc:
            logger.exception(f"Erreur en démarrant le mode watch: {exc}")
            raise
    else:
        # mode manuel -> envoi + backup
        send_and_backup()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        logger.exception(f"Crash inattendu: {exc}")
        raise
