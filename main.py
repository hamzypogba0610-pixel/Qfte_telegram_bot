import logging
import os
from pprint import pformat
import re
import sqlite3

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


FORMAT_EXAMPLE = """Arsenal vs Liverpool
Football - Premier League
Over 2.5 : 1.85
Under 2.5 : 2.00"""

HELP_TEXT = """Pour recevoir une analyse structurée, envoyez un rapport complet
sur un match de football. Utilisez de préférence ce format :

Équipe à domicile vs Équipe à l'extérieur
Compétition : Premier League
Date et heure :
Dernier match de chaque équipe :
Prochain match de chaque équipe :
Jours de repos :
Déplacement :
Risque de rotation :
Match important à venir :
Ligne Over/Under et cotes :
Ligne de handicap et cotes :
Forme récente, absences et suspensions :

Utilisez /debug pour afficher le dictionnaire du dernier match reçu.
Utilisez /historique pour voir les cinq derniers matchs enregistrés.

Le bot indique les informations présentes et celles qui manquent. Il ne
fabrique ni probabilité ni garantie de résultat ou de gain."""

MATCH_PATTERN = re.compile(
    r"(?P<team_a>[^\n]+?)\s+vs\s+(?P<team_b>[^\n]+)",
    flags=re.IGNORECASE,
)

MATCH_DATA_FIELDS = (
    "home_team",
    "away_team",
    "competition",
    "date_time",
    "last_match_home",
    "last_match_away",
    "next_match_home",
    "next_match_away",
    "rest_days_home",
    "rest_days_away",
    "travel_info",
    "rotation_risk",
    "important_upcoming_match",
    "over_under_line",
    "over_odds",
    "under_odds",
    "handicap_line",
    "handicap_odds",
    "form",
    "absences",
    "suspensions",
)

# The latest parsed report, kept in memory for /debug.
match_data: dict[str, str | None] = {
    field: None for field in MATCH_DATA_FIELDS
}

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "qfte_matches.db",
)

CALENDAR_FIELDS = (
    ("Dernier match", ("dernier match", "last match", "match précédent")),
    ("Prochain match", ("prochain match", "next match", "match suivant")),
    ("Jours de repos", ("jours de repos", "repos", "days of rest")),
    ("Déplacement", ("déplacement", "deplacement", "travel", "voyage")),
    (
        "Risque de rotation",
        ("rotation", "risque de rotation", "turnover"),
    ),
    (
        "Match important à venir",
        (
            "match important",
            "important future match",
            "match à venir",
            "match a venir",
        ),
    ),
)


def clean_team_name(team_name: str) -> str:
    """Remove an optional label before the home team name."""
    return re.sub(
        r"^\s*(?:match|rencontre)\s*[:\-]\s*",
        "",
        team_name,
        flags=re.IGNORECASE,
    ).strip(" \t:-–—")


def find_line_with_keywords(
    text: str, keywords: tuple[str, ...]
) -> str | None:
    """Return the first report line containing one of the keywords."""
    for line in text.splitlines():
        cleaned_line = line.strip()
        lowered_line = cleaned_line.casefold()
        if cleaned_line and any(keyword in lowered_line for keyword in keywords):
            return cleaned_line
    return None


def find_labeled_value(
    text: str, labels: tuple[str, ...]
) -> str | None:
    """Find the value after a label such as 'Compétition :'."""
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"^\s*(?:{label_pattern})\s*[:=\-]\s*(?P<value>.*?)\s*$",
        flags=re.IGNORECASE,
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if match and match.group("value").strip():
            return match.group("value").strip()
    return None


def find_market_line(
    text: str, market: str
) -> tuple[str | None, str | None]:
    """Extract a market line and odds from common Over/Under formats."""
    if market == "over":
        pattern = re.compile(
            r"^\s*(?:over|plus\s+de)\s*"
            r"(?P<line>\d+(?:[.,]\d+)?)\s*"
            r"(?:[:=@/]|-\s*)\s*"
            r"(?P<odds>\d+(?:[.,]\d+)?)\s*$",
            flags=re.IGNORECASE,
        )
    elif market == "under":
        pattern = re.compile(
            r"^\s*(?:under|moins\s+de)\s*"
            r"(?P<line>\d+(?:[.,]\d+)?)\s*"
            r"(?:[:=@/]|-\s*)\s*"
            r"(?P<odds>\d+(?:[.,]\d+)?)\s*$",
            flags=re.IGNORECASE,
        )
    else:
        pattern = re.compile(
            r"^\s*(?:handicap|spread)"
            r"\s*(?:[:=]\s*)?(?P<line>[+-]?\d+(?:[.,]\d+)?)\s*"
            r"(?:[:=@/]|-\s*)\s*"
            r"(?P<odds>\d+(?:[.,]\d+)?)\s*$",
            flags=re.IGNORECASE,
        )

    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group("line"), match.group("odds")
    return None, None


def parse_match_data(
    text: str, home_team: str, away_team: str
) -> dict[str, str | None]:
    """Parse a match report into the public match_data dictionary shape."""
    over_line, over_odds = find_market_line(text, "over")
    under_line, under_odds = find_market_line(text, "under")
    handicap_line, handicap_odds = find_market_line(text, "handicap")

    date_time = find_labeled_value(
        text,
        (
            "date et heure",
            "date/heure",
            "date_time",
            "date",
            "heure",
            "coup d'envoi",
            "coup d’envoi",
            "kick-off",
        ),
    )
    if date_time is None:
        date_value = find_labeled_value(text, ("date",))
        time_value = find_labeled_value(text, ("heure", "kick-off"))
        if date_value and time_value:
            date_time = f"{date_value} {time_value}"
        else:
            date_time = date_value or time_value

    data = {
        "home_team": home_team or None,
        "away_team": away_team or None,
        "competition": find_competition(text),
        "date_time": date_time,
        "last_match_home": find_labeled_value(
            text,
            (
                "dernier match domicile",
                "dernier match à domicile",
                "last match home",
            ),
        ),
        "last_match_away": find_labeled_value(
            text,
            (
                "dernier match extérieur",
                "dernier match à l'extérieur",
                "last match away",
            ),
        ),
        "next_match_home": find_labeled_value(
            text,
            (
                "prochain match domicile",
                "prochain match à domicile",
                "next match home",
            ),
        ),
        "next_match_away": find_labeled_value(
            text,
            (
                "prochain match extérieur",
                "prochain match à l'extérieur",
                "next match away",
            ),
        ),
        "rest_days_home": find_labeled_value(
            text,
            (
                "jours de repos domicile",
                "repos domicile",
                "rest days home",
            ),
        ),
        "rest_days_away": find_labeled_value(
            text,
            (
                "jours de repos extérieur",
                "jours de repos à l'extérieur",
                "repos extérieur",
                "rest days away",
            ),
        ),
        "travel_info": find_labeled_value(
            text,
            ("déplacement", "deplacement", "travel", "voyage"),
        ),
        "rotation_risk": find_labeled_value(
            text,
            ("risque de rotation", "rotation risk", "rotation", "turnover"),
        ),
        "important_upcoming_match": find_labeled_value(
            text,
            (
                "match important à venir",
                "match important a venir",
                "important upcoming match",
                "important future match",
            ),
        ),
        "over_under_line": (
            over_line
            or under_line
            or find_labeled_value(
                text,
                (
                    "ligne over/under",
                    "ligne over under",
                    "over/under line",
                ),
            )
        ),
        "over_odds": over_odds
        or find_labeled_value(text, ("cote over", "over odds")),
        "under_odds": under_odds
        or find_labeled_value(text, ("cote under", "under odds")),
        "handicap_line": handicap_line
        or find_labeled_value(
            text, ("ligne handicap", "handicap line")
        ),
        "handicap_odds": handicap_odds
        or find_labeled_value(
            text, ("cote handicap", "handicap odds")
        ),
        "form": find_labeled_value(
            text, ("forme récente", "forme", "recent form", "form")
        ),
        "absences": find_labeled_value(
            text, ("absences", "absence", "blessures", "injuries")
        ),
        "suspensions": find_labeled_value(
            text, ("suspensions", "suspension", "suspended")
        ),
    }

    return {field: data.get(field) for field in MATCH_DATA_FIELDS}


def to_float(value: object) -> float | None:
    """Convert a parsed decimal value into a SQLite REAL value."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    try:
        return float(value.replace(",", ".").strip())
    except ValueError:
        return None


def to_int(value: object) -> int | None:
    """Convert a parsed rest-day value into a SQLite INTEGER value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group()) if match else None


def is_present(value: object) -> bool:
    """Return whether a parsed field contains usable text or a number."""
    return value is not None and str(value).strip() != ""


def analyze_match(match_data: dict[str, object]) -> dict[str, object]:
    """Apply the optimized QFTE scoring and verdict rules."""
    rest_values = [
        rest_days
        for rest_days in (
            to_int(match_data.get("rest_days_home")),
            to_int(match_data.get("rest_days_away")),
        )
        if rest_days is not None
    ]
    minimum_rest = min(rest_values) if rest_values else None

    calendar_score = 0
    if minimum_rest is not None:
        if minimum_rest >= 4:
            calendar_score += 3
        elif minimum_rest == 3:
            calendar_score += 2
        elif minimum_rest == 2:
            calendar_score += 1

    travel_text = str(match_data.get("travel_info") or "").casefold()
    travel_distance = re.search(
        r"(\d+(?:[.,]\d+)?)\s*km",
        travel_text,
    )
    if not travel_text or any(
        phrase in travel_text
        for phrase in (
            "aucun",
            "sans déplacement",
            "sans deplacement",
            "no travel",
            "pas de déplacement",
            "pas de deplacement",
        )
    ):
        calendar_score += 2
    elif travel_distance and float(
        travel_distance.group(1).replace(",", ".")
    ) <= 500:
        calendar_score += 2

    rotation_text = str(match_data.get("rotation_risk") or "").casefold()
    if any(term in rotation_text for term in ("low", "faible", "bas")):
        calendar_score += 3
    elif any(
        term in rotation_text
        for term in ("medium", "moyen", "modéré", "modere")
    ):
        calendar_score += 1

    important_match = str(
        match_data.get("important_upcoming_match") or ""
    ).casefold()
    important_days = re.search(
        r"(?:dans|in|within)\s*(?:les?\s*)?(\d+)\s*"
        r"(?:jours?|days?)",
        important_match,
    )
    if important_days and int(important_days.group(1)) <= 3:
        calendar_score -= 2
    calendar_score = max(0, min(10, calendar_score))

    data_quality_score = 0
    if is_present(match_data.get("home_team")) and is_present(
        match_data.get("away_team")
    ):
        data_quality_score += 1
    if is_present(match_data.get("competition")):
        data_quality_score += 1
    if is_present(match_data.get("date_time")):
        data_quality_score += 1
    if is_present(match_data.get("over_odds")) and is_present(
        match_data.get("under_odds")
    ):
        data_quality_score += 2
    if is_present(match_data.get("handicap_line")) and is_present(
        match_data.get("handicap_odds")
    ):
        data_quality_score += 2
    if is_present(match_data.get("last_match_home")) or is_present(
        match_data.get("last_match_away")
    ):
        data_quality_score += 1
    if is_present(match_data.get("next_match_home")) or is_present(
        match_data.get("next_match_away")
    ):
        data_quality_score += 1
    if is_present(match_data.get("absences")) or is_present(
        match_data.get("suspensions")
    ):
        data_quality_score += 2
    data_quality_score = min(10, data_quality_score)

    if data_quality_score >= 7 and calendar_score >= 6:
        over_under_verdict = "PLAY"
    elif data_quality_score >= 5 and calendar_score >= 4:
        over_under_verdict = "WAIT"
    else:
        over_under_verdict = "AVOID"

    if data_quality_score >= 7 and calendar_score >= 7:
        handicap_verdict = "PLAY"
    elif data_quality_score >= 5 and calendar_score >= 5:
        handicap_verdict = "WAIT"
    else:
        handicap_verdict = "AVOID"

    if calendar_score <= 3:
        final_decision = "AVOID"
    elif data_quality_score <= 4:
        final_decision = "WAIT"
    elif (
        over_under_verdict == "PLAY"
        and handicap_verdict == "PLAY"
    ):
        final_decision = "PLAY"
    else:
        final_decision = "WAIT"

    score_scenarios = [
        "Scénario 1 (match fermé) : 0-0, 1-0, 0-1.",
        "Scénario 2 (match équilibré) : 1-1, 2-1, 1-2.",
        "Scénario 3 (match ouvert) : 2-2, 3-1, 1-3.",
    ]

    return {
        "calendar_score": calendar_score,
        "data_quality_score": data_quality_score,
        "over_under_verdict": over_under_verdict,
        "handicap_verdict": handicap_verdict,
        "score_scenarios": score_scenarios,
        "final_decision": final_decision,
        "warning": (
            "Aucun résultat sportif ni bénéfice de pari n'est garanti. "
            "Ces règles ne remplacent pas une vérification indépendante "
            "des données pré-match."
        ),
    }


def init_database() -> None:
    """Create the matches table if it does not already exist."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT,
                away_team TEXT,
                competition TEXT,
                date_time TEXT,
                over_under_line TEXT,
                over_odds REAL,
                under_odds REAL,
                handicap_line TEXT,
                handicap_odds REAL,
                rest_days_home INTEGER,
                rest_days_away INTEGER,
                rotation_risk TEXT,
                form TEXT,
                absences TEXT,
                suspensions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_match(match: dict[str, str | None]) -> None:
    """Insert one parsed match dictionary into the matches table."""
    init_database()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO matches (
                home_team,
                away_team,
                competition,
                date_time,
                over_under_line,
                over_odds,
                under_odds,
                handicap_line,
                handicap_odds,
                rest_days_home,
                rest_days_away,
                rotation_risk,
                form,
                absences,
                suspensions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match.get("home_team"),
                match.get("away_team"),
                match.get("competition"),
                match.get("date_time"),
                match.get("over_under_line"),
                to_float(match.get("over_odds")),
                to_float(match.get("under_odds")),
                match.get("handicap_line"),
                to_float(match.get("handicap_odds")),
                to_int(match.get("rest_days_home")),
                to_int(match.get("rest_days_away")),
                match.get("rotation_risk"),
                match.get("form"),
                match.get("absences"),
                match.get("suspensions"),
            ),
        )
        connection.commit()

    logger.info(
        "Match enregistré dans SQLite : %s vs %s",
        match.get("home_team"),
        match.get("away_team"),
    )


def get_recent_matches(limit: int = 5) -> list[dict[str, object]]:
    """Return the newest saved matches first."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                home_team,
                away_team,
                competition,
                date_time,
                over_odds,
                under_odds,
                created_at
            FROM matches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def format_odds(value: object) -> str:
    """Format saved odds consistently for the history response."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)


def find_competition(text: str) -> str | None:
    """Find a competition from an explicit label or a football competition line."""
    for line in text.splitlines():
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        explicit_match = re.match(
            r"^(?:compétition|competition)\s*[:\-]\s*(.+)$",
            cleaned_line,
            flags=re.IGNORECASE,
        )
        if explicit_match:
            return explicit_match.group(1).strip()

        football_match = re.match(
            r"^football\s*[-:]\s*(.+)$",
            cleaned_line,
            flags=re.IGNORECASE,
        )
        if football_match:
            return football_match.group(1).strip()

    known_competitions = (
        "premier league",
        "ligue 1",
        "la liga",
        "serie a",
        "bundesliga",
        "champions league",
        "europa league",
        "conference league",
        "fa cup",
        "coupe du monde",
        "coupe d'afrique",
        "mls",
    )
    for line in text.splitlines():
        cleaned_line = line.strip()
        if any(
            competition in cleaned_line.casefold()
            for competition in known_competitions
        ):
            return cleaned_line

    return None


def build_match_report(
    text: str,
    team_a: str,
    team_b: str,
    parsed_data: dict[str, object] | None = None,
) -> str:
    """Build a cautious, structured French report from the submitted text."""
    parsed = parsed_data or parse_match_data(text, team_a, team_b)
    competition = find_competition(text)
    date_or_time = find_line_with_keywords(
        text,
        ("date", "heure", "coup d'envoi", "coup d’envoi", "kick-off"),
    )
    over_under = find_line_with_keywords(
        text, ("over", "under", "plus de", "moins de", "cote", "odds")
    )
    handicap = find_line_with_keywords(text, ("handicap", "spread"))
    form_or_availability = find_line_with_keywords(
        text,
        (
            "forme récente",
            "forme",
            "absenc",
            "bless",
            "suspend",
            "injur",
        ),
    )

    quality_items = [
        f"- Équipes : détectées — {team_a} / {team_b}",
        (
            f"- Compétition : détectée — {competition}"
            if competition
            else "- Compétition : manquante — à fournir"
        ),
        (
            f"- Date et heure : détectées — {date_or_time}"
            if date_or_time
            else "- Date et heure : manquantes — à fournir"
        ),
        (
            f"- Données Over/Under ou cotes : présentes dans le message — {over_under}"
            if over_under
            else "- Données Over/Under ou cotes : manquantes — à vérifier"
        ),
        (
            f"- Handicap et cotes : présents dans le message — {handicap}"
            if handicap
            else "- Handicap et cotes : manquants — à fournir"
        ),
        (
            f"- Forme, absences et suspensions : présentes — {form_or_availability}"
            if form_or_availability
            else "- Forme, absences et suspensions : manquantes — à vérifier"
        ),
    ]

    calendar_items = []
    for label, keywords in CALENDAR_FIELDS:
        value = find_line_with_keywords(text, keywords)
        if value:
            calendar_items.append(f"- {label} : identifié — {value}")
        else:
            calendar_items.append(f"- {label} : à identifier ou à fournir")

    analysis = analyze_match(parsed)
    analysis_lines = [
        "",
        "ANALYSE QFTE",
        f"1. SCORE CALENDRIER : {analysis['calendar_score']}/10",
        f"2. QUALITÉ DES DONNÉES : {analysis['data_quality_score']}/10",
        f"3. VERDICT OVER/UNDER : {analysis['over_under_verdict']}",
        f"4. VERDICT HANDICAP : {analysis['handicap_verdict']}",
        "5. SCÉNARIOS DE SCORE :",
        *[
            f"- {scenario}"
            for scenario in analysis["score_scenarios"]
        ],
        f"6. DÉCISION FINALE : {analysis['final_decision']}",
        f"7. AVERTISSEMENT : {analysis['warning']}",
    ]

    return "\n".join(
        [
            "1. MATCH REÇU",
            f"- Équipe à domicile : {team_a}",
            f"- Équipe à l'extérieur : {team_b}",
            f"- Compétition : {competition or 'non indiquée'}",
            "",
            "2. QUALITÉ DES DONNÉES",
            *quality_items,
            "",
            "3. CHECKLIST CALENDRIER",
            *calendar_items,
            "",
            "4. OVER/UNDER",
            (
                "Une recommandation fiable nécessite des données pré-match "
                "vérifiées et les cotes disponibles."
            ),
            "Aucune probabilité n'est inventée à partir d'informations incomplètes.",
            "VERDICT : ATTENDRE / DONNÉES INSUFFISANTES",
            "",
            "5. HANDICAP",
            (
                "Une décision de handicap nécessite une ligne spécifique "
                "disponible et ses cotes. Sans ligne et cotes vérifiées, "
                "aucun verdict fiable ne peut être donné."
            ),
            "",
            "6. SCÉNARIOS DE SCORE EXACT (QUALITATIFS)",
            (
                "- Scénario 1 — match fermé : rythme prudent et écart limité, "
                "par exemple 0-0, 1-0 ou 0-1."
            ),
            (
                "- Scénario 2 — match équilibré : les deux équipes créent des "
                "occasions, par exemple 1-1 ou 2-1."
            ),
            (
                "- Scénario 3 — match ouvert : plusieurs occasions et score "
                "plus élevé, par exemple 2-2, 3-1 ou 1-3."
            ),
            "Ces scénarios sont illustratifs, sans probabilité ni recommandation.",
            "",
            "7. AVERTISSEMENT FINAL",
            (
                "Aucun résultat sportif ni bénéfice de pari n'est garanti. "
                "Vérifiez toujours les informations et pariez de façon responsable."
            ),
            *analysis_lines,
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome a user in French."""
    if update.message:
        await update.message.reply_text(
            "Bienvenue sur le bot QFTE !\n"
            "Envoyez un match au format « Équipe A vs Équipe B » "
            "pour qu'il soit reçu."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm that the bot is active."""
    if update.message:
        await update.message.reply_text(
            "✅ Le bot QFTE est actif et prêt à recevoir un match."
        )


async def show_format(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the expected match format."""
    if update.message:
        await update.message.reply_text(FORMAT_EXAMPLE)


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Explain how to submit a complete football match report."""
    if update.message:
        await update.message.reply_text(HELP_TEXT)


async def debug_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the latest parsed match_data dictionary."""
    if not update.message:
        return

    if match_data["home_team"] is None:
        await update.message.reply_text(
            "Aucun match n'a encore été reçu. Envoyez d'abord un rapport "
            "contenant « Équipe A vs Équipe B »."
        )
        return

    await update.message.reply_text(
        "match_data =\n"
        + pformat(match_data, sort_dicts=False, width=80)
    )


async def history_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the five most recently saved matches."""
    if not update.message:
        return

    try:
        recent_matches = get_recent_matches()
    except sqlite3.Error:
        logger.exception("Impossible de lire l'historique des matchs.")
        await update.message.reply_text(
            "⚠️ Impossible de lire l'historique pour le moment."
        )
        return

    if not recent_matches:
        await update.message.reply_text(
            "Aucun match n'est encore enregistré dans l'historique."
        )
        return

    lines = ["📚 HISTORIQUE — 5 DERNIERS MATCHS"]
    for index, saved_match in enumerate(recent_matches, start=1):
        home_team = saved_match.get("home_team") or "non indiqué"
        away_team = saved_match.get("away_team") or "non indiqué"
        competition = saved_match.get("competition") or "non indiquée"
        date_time = saved_match.get("date_time") or "non indiquée"
        created_at = saved_match.get("created_at") or "non indiqué"
        lines.extend(
            [
                "",
                f"{index}. {home_team} vs {away_team}",
                f"Compétition : {competition}",
                f"Date/heure : {date_time}",
            ]
        )

        over_odds = saved_match.get("over_odds")
        under_odds = saved_match.get("under_odds")
        if over_odds is not None or under_odds is not None:
            lines.append(
                "Cotes : "
                f"Over {format_odds(over_odds) if over_odds is not None else '—'} / "
                f"Under {format_odds(under_odds) if under_odds is not None else '—'}"
            )
        lines.append(f"Enregistré le : {created_at}")

    await update.message.reply_text("\n".join(lines))


async def receive_match(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receive a match report and return a cautious structured response."""
    if not update.message or not update.message.text:
        return

    match = MATCH_PATTERN.search(update.message.text)
    if not match:
        return

    team_a = match.group("team_a").strip()
    team_b = match.group("team_b").strip()
    home_team = clean_team_name(team_a)
    away_team = team_b.strip(" \t:-–—")

    global match_data
    match_data = parse_match_data(update.message.text, home_team, away_team)

    try:
        # Save immediately after parsing and before building or sending analysis.
        save_match(match_data)
    except sqlite3.Error:
        logger.exception("Impossible d'enregistrer le match.")
        await update.message.reply_text(
            "⚠️ Le match a été analysé, mais son enregistrement a échoué."
        )
        return

    await update.message.reply_text(
        build_match_report(
            update.message.text,
            home_team,
            away_team,
            match_data,
        )
    )


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log unexpected Telegram errors without exposing the bot token."""
    logger.error("Une erreur Telegram est survenue: %s", context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Le Secret TELEGRAM_BOT_TOKEN est introuvable. "
            "Ajoutez-le dans Replit avant de lancer le bot."
        )

    init_database()
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("statut", status))
    application.add_handler(CommandHandler("format", show_format))
    application.add_handler(CommandHandler("aide", help_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("historique", history_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_match)
    )
    application.add_error_handler(error_handler)

    logger.info("Bot QFTE démarré.")
    application.run_polling()


if __name__ == "__main__":
    main()