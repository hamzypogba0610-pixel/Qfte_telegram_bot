# Bot Telegram QFTE

Bot Telegram Python qui répond en français aux commandes QFTE et reçoit des
matchs au format `Équipe A vs Équipe B`.

## Lancer le bot

1. Le token Telegram doit être enregistré dans le Secret Replit nommé
   `TELEGRAM_BOT_TOKEN`.
2. Lancez `python main.py`.

Le bot utilise le mode polling : laissez le processus en marche pour qu'il
continue à recevoir les messages.

## Commandes

- `/start` — message de bienvenue
- `/statut` — vérifie que le bot est actif
- `/format` — affiche le format d'exemple
- `/aide` — explique comment envoyer un rapport complet
- `/debug` — affiche le dictionnaire du dernier match reçu
- `/historique` — affiche les cinq derniers matchs enregistrés

Un message comme `Arsenal vs Liverpool` est automatiquement reçu et traité
avec les équipes, la compétition détectée, la qualité des données, la
checklist du calendrier et des scénarios qualitatifs sans fausses probabilités.

Les rapports reçus sont enregistrés dans la base SQLite locale
`qfte_matches.db`.