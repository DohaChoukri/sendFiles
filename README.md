# 📁 Envoi automatique des fichiers depuis le backup

Ce projet permet d’automatiser l’envoi des fichiers sauvegardés par email, avec notification et nettoyage automatique du dossier de backup.

## 🚀 Fonctionnalités

- 📤 **Envoi automatique des fichiers depuis le dossier de sauvegarde**
  - Tous les fichiers ajoutés dans le dossier `backup` sont détectés automatiquement.
  - Les fichiers sont envoyés par email aux destinataires configurés.

- 📧 **Notification par email**
  - Un email est envoyé pour confirmer que les fichiers ont été correctement sauvegardés et envoyés.
  - En cas d’erreur, une notification email est également envoyée.

- 🧹 **Nettoyage automatique du backup**
  - Après un envoi réussi, les fichiers sont supprimés automatiquement du dossier de sauvegarde afin d’éviter les doublons et libérer l’espace disque.

- 📝 **Gestion des erreurs et logs**
  - Toutes les actions (envoi, sauvegarde, suppression, erreurs) sont enregistrées dans un fichier de log.
  - Rotation des logs pour éviter des fichiers trop volumineux.

- 👀 **Mode surveillance (watch)**
  - Surveillance en temps réel du dossier de sauvegarde.
  - Déclenchement automatique de l’envoi dès qu’un nouveau fichier est ajouté.

## ⚙️ Mode de fonctionnement

1. Un fichier est ajouté dans le dossier de sauvegarde.
2. Le script détecte le nouveau fichier.
3. Le fichier est envoyé par email.
4. Un email de notification est envoyé pour confirmer l’opération.
5. Le fichier est supprimé du dossier de sauvegarde après envoi réussi.

## 🛠️ Technologies utilisées

- Python
- SMTP (envoi d’emails)
- Watchdog (surveillance des dossiers)
- Logging avec rotation des fichiers
- Variables d’environnement (`.env`)

## ▶️ Lancement

```bash
python send_files.py --watch
