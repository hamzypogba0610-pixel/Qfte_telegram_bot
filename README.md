# QFTE V13 — Quantitative Futures & Telegram Engine

Moteur de trading quantitatif pour futures crypto avec interface Telegram.

## Structure
qfte-v13/
├── app/
│   └── main.py
├── data/
├── logs/
├── tests/
├── bot.py
├── config.py
├── logging_config.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md

## Installation

```bash
# Cloner le dépôt
git clone [https://github.com/ton-username/qfte-v13.git](https://github.com/ton-username/qfte-v13.git)
cd qfte-v13

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venvScriptsactivate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier .env.example en .env et remplir les valeurs
cp .env.example .env

## Configuration

Édite `.env` et remplis :

- `TELEGRAM_BOT_TOKEN` : Token de ton bot Telegram
- `TELEGRAM_ADMIN_IDS` : IDs des admins (séparés par des virgules)

## Lancement

```bash
# Lancer le bot Telegram
python bot.py

# Lancer l'API FastAPI
uvicorn app.main:app --reload

## Licence

MIT
