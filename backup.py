import os
import shutil


def ensure_backup_dir(backup_dir, logger=None):
    try:
        os.makedirs(backup_dir, exist_ok=True)
        if logger:
            logger.info(f"Dossier de sauvegarde vérifié/créé: {backup_dir}")
        return True
    except Exception as e:
        if logger:
            logger.exception(f"Impossible de créer/le vérifier le dossier de sauvegarde {backup_dir}: {e}")
        return False


def copy_files_to_backup(files, backup_dir, logger=None):
    copied = []
    for f in files:
        try:
            dest = os.path.join(backup_dir, os.path.basename(f))
            shutil.copy2(f, dest)
            copied.append(dest)
            if logger:
                logger.info(f"Copié vers sauvegarde: {dest}")
        except Exception as e:
            if logger:
                logger.error(f"Erreur copie vers sauvegarde {f}: {e}")
    return copied


def cleanup_success_in_source(source_dir, logger=None):
    removed = []
    try:
        for fpath in os.listdir(source_dir):
            full = os.path.join(source_dir, fpath)
            if os.path.isfile(full) and full.endswith('.success'):
                try:
                    os.remove(full)
                    removed.append(full)
                    if logger:
                        logger.info(f"Supprimé .success dans source: {full}")
                except Exception as e:
                    if logger:
                        logger.error(f"Impossible de supprimer {full}: {e}")
    except Exception as e:
        if logger:
            logger.exception(f"Erreur lors de la suppression des fichiers .success dans {source_dir}: {e}")
    return removed


def process_success_files(source_dir, backup_dir, logger=None):
    """Traite les fichiers existants se terminant par .success :
    - copie chaque fichier vers backup en enlevant le suffixe '.success'
    - supprime le fichier .success dans la source
    Retourne la liste des fichiers copiés (dest paths) et supprimés (source paths)
    """
    copied = []
    removed = []

    try:
        for fpath in os.listdir(source_dir):
            full = os.path.join(source_dir, fpath)
            if os.path.isfile(full) and full.endswith('.success'):
                try:
                    orig_name = fpath[:-len('.success')]
                    dest = os.path.join(backup_dir, orig_name)
                    shutil.copy2(full, dest)
                    copied.append(dest)
                    if logger:
                        logger.info(f"Copié depuis .success vers sauvegarde: {full} -> {dest}")
                except Exception as e:
                    if logger:
                        logger.error(f"Erreur copie depuis .success {full}: {e}")
                    continue

                try:
                    os.remove(full)
                    removed.append(full)
                    if logger:
                        logger.info(f"Supprimé .success après copie: {full}")
                except Exception as e:
                    if logger:
                        logger.error(f"Impossible de supprimer {full} après copie: {e}")
    except Exception as e:
        if logger:
            logger.exception(f"Erreur lors du traitement des fichiers .success dans {source_dir}: {e}")

    return copied, removed