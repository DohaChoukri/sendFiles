# 📁 Envoi automatique des fichiers depuis le backup

Ce projet permet d’automatiser l’envoi par email des fichiers présents dans un dossier de sauvegarde, avec **contrôle des extensions**, **notification**, et **nettoyage automatique** après traitement.

---

## 🚀 Fonctionnalités

### 📤 Envoi automatique des fichiers autorisés
- Détection automatique des fichiers ajoutés dans le dossier `backup`
- **Vérification des extensions autorisées avant traitement**
- Seuls les fichiers conformes sont envoyés par email aux destinataires configurés
- Les fichiers non autorisés sont ignorés (ni envoyés, ni sauvegardés)

### 📧 Notification par email
- Envoi d’un email de confirmation après un envoi réussi
- Envoi d’un email d’alerte en cas d’erreur lors du traitement

### 🧹 Nettoyage automatique du backup
- Suppression automatique des fichiers envoyés après succès
- Prévention des doublons et optimisation de l’espace disque

### 📝 Gestion des erreurs et logs
- Journalisation complète des actions : détection, envoi, nettoyage, erreurs
- Rotation automatique des fichiers de logs pour éviter leur surcharge

### 👀 Mode surveillance (watch)
- Surveillance en temps réel du dossier de sauvegarde
- Déclenchement immédiat du traitement dès l’ajout d’un nouveau fichier

---

## ⚙️ Règles de traitement des fichiers

| Type de fichier | Action |
|----------------|--------|
| Extension autorisée | ✔️ Envoyé par email puis supprimé du backup |
| Extension non autorisée | ❌ Ignoré (aucune sauvegarde) |

---

## ⚙️ Mode de fonctionnement

1. Un fichier est ajouté dans le dossier de sauvegarde (`backup`)
2. Le script détecte automatiquement le fichier
3. L’extension du fichier est vérifiée
4. Si autorisée :
   - le fichier est envoyé par email
   - une notification de succès est envoyée
   - le fichier est supprimé du dossier de sauvegarde
5. Toutes les actions sont enregistrées dans les logs

---

## 🛠️ Technologies utilisées

- Python
- SMTP (envoi d’emails)
- Watchdog (surveillance des dossiers)
- Logging avec rotation des fichiers
- Variables d’environnement (`.env`)

---

## ▶️ Lancement

### Mode surveillance (recommandé)

```bash
python send_files.py --watch
