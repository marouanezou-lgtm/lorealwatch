# Surveillance inscription Défilé L'Oréal Paris 2026

Vérifie automatiquement toutes les 5 minutes si les inscriptions sont
ouvertes sur `inscription-defilelorealparis2026.event-loreal.com` et
envoie une alerte push iPhone, un email et un message WhatsApp dès que
c'est le cas.

## Mise en place (environ 15 minutes)

### 1. Créer le dépôt GitHub

1. Va sur https://github.com/new
2. Nom du dépôt : `loreal-watch` (ou ce que tu veux)
3. Visibilité : **Public** (pour avoir des minutes GitHub Actions illimitées gratuites ;
   si tu préfères le garder privé, ça marche aussi mais avec un quota de minutes)
4. Crée le dépôt, puis dépose tous les fichiers de ce dossier dedans
   (`check_registration.py`, `requirements.txt`, `.github/workflows/check.yml`)
5. Committe et pousse (`git add . && git commit -m "init" && git push`)

### 2. Notification push iPhone (ntfy) — 2 minutes

1. Installe l'app gratuite **ntfy** sur ton iPhone (App Store).
2. Choisis un nom de "topic" unique et difficile à deviner par quelqu'un
   d'autre, par exemple `marouane-loreal-9f3k2`.
3. Dans l'app, abonne-toi (Subscribe) à ce topic.
4. Dans GitHub : Settings → Secrets and variables → Actions → New repository
   secret :
   - `NTFY_TOPIC` = `marouane-loreal-9f3k2`

### 3. Email — 5 minutes (exemple avec Gmail)

1. Active la validation en deux étapes sur ton compte Google si ce n'est
   pas déjà fait.
2. Va sur https://myaccount.google.com/apppasswords et crée un
   "mot de passe d'application" (nom libre, ex. "loreal-watch").
3. Ajoute ces secrets GitHub :
   - `EMAIL_HOST` = `smtp.gmail.com`
   - `EMAIL_PORT` = `465`
   - `EMAIL_USER` = ton adresse Gmail complète
   - `EMAIL_PASSWORD` = le mot de passe d'application généré (pas ton mot de passe normal)
   - `EMAIL_TO` = l'adresse où tu veux recevoir l'alerte (peut être la même)

### 4. WhatsApp (CallMeBot) — 5 minutes

1. Ajoute ce numéro à tes contacts WhatsApp : **+34 644 66 03 79**
2. Envoie-lui le message : `I allow callmebot to send me messages`
3. Tu reçois en retour ton `apikey` personnel (un nombre).
4. Ajoute ces secrets GitHub :
   - `WHATSAPP_PHONE` = ton numéro au format international, ex. `+33612345678`
   - `WHATSAPP_APIKEY` = la clé reçue

Tu n'es pas obligé d'activer les trois canaux : le script ignore
simplement ceux dont les secrets ne sont pas renseignés.

### 5. Vérifier que ça tourne

- Onglet **Actions** du dépôt → le workflow "Vérifier inscription Défilé
  L'Oréal Paris" doit apparaître et se lancer toutes les 5 minutes.
- Tu peux le déclencher manuellement tout de suite via le bouton
  "Run workflow" pour tester que les notifications arrivent bien.

## Comment ça détecte l'ouverture

La page est en JavaScript (React), donc le script utilise un vrai
navigateur headless (Playwright) pour voir le contenu réellement affiché,
pas juste le HTML brut. Il cherche :

- la présence d'un formulaire / champ de saisie sur la page, **et**
- des mots comme "s'inscrire", "réserver ma place", **et l'absence** de
  mots comme "bientôt", "prochainement".

En filet de sécurité, si le contenu de la page change de façon notable
sans matcher ces mots-clés exactement, tu reçois quand même une alerte
"changement détecté" (au maximum 2 fois) pour vérifier manuellement.

Une fois l'ouverture détectée et notifiée, le script arrête de
retélécharger la page (il lit `state.json`) pour ne pas te spammer ni
gaspiller des minutes GitHub Actions.

## Limites à connaître

- Les workflows planifiés GitHub peuvent avoir quelques minutes de
  retard aux heures de forte charge (rare, mais possible).
- Si le site change complètement sa structure ou son texte par rapport
  à ce qui est prévu ici, ajuste les listes `CLOSED_KEYWORDS` /
  `OPEN_KEYWORDS` dans `check_registration.py`.
- GitHub désactive automatiquement les workflows planifiés après 60
  jours sans activité sur le dépôt — largement suffisant ici.
