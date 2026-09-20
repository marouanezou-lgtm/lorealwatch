#!/usr/bin/env python3
"""
Surveille la page d'inscription au Défilé L'Oréal Paris 2026 et envoie une
notification (push iPhone via ntfy.sh, email, WhatsApp via CallMeBot) dès
que les inscriptions semblent ouvertes.

État persisté dans state.json (committé dans le dépôt par le workflow
GitHub Actions) pour ne pas notifier plusieurs fois pour la même ouverture.
"""

import hashlib
import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

URL = "https://inscription-defilelorealparis2026.event-loreal.com/fr/"
STATE_PATH = Path(__file__).parent / "state.json"

# Mots-clés indiquant que les inscriptions ne sont PAS encore ouvertes.
CLOSED_KEYWORDS = [
    "bientôt",
    "bientot",
    "à venir",
    "prochainement",
    "restez informé",
    "restez informés",
    "revenez bientôt",
    "ouverture prochaine",
    "pas encore ouvert",
]

# Mots-clés indiquant qu'un vrai formulaire d'inscription est présent.
OPEN_KEYWORDS = [
    "s'inscrire",
    "je m'inscris",
    "réserver ma place",
    "réserver votre place",
    "compléter le formulaire",
    "demande d'inscription",
]


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_hash": None, "open_notified": False, "change_notices_sent": 0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def fetch_rendered_page() -> tuple[str, bool]:
    """Retourne (texte visible normalisé, présence d'un <form>/<input>)."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)  # laisser le JS finir de rendre
        text = page.inner_text("body")
        has_form = page.locator("form").count() > 0 or page.locator(
            "input[type='email'], input[type='text']"
        ).count() > 0
        browser.close()
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return normalized, has_form


def determine_status(text: str, has_form: bool) -> str:
    has_closed = any(k in text for k in CLOSED_KEYWORDS)
    has_open_kw = any(k in text for k in OPEN_KEYWORDS)
    if has_form and has_open_kw and not has_closed:
        return "open"
    if has_closed:
        return "closed"
    return "unknown"


def send_ntfy(title: str, message: str) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Priority": "urgent",
                "Tags": "rotating_light",
                "Click": URL,
            },
            timeout=15,
        )
    except Exception as e:
        print(f"[ntfy] échec: {e}", file=sys.stderr)


def send_email(subject: str, body: str) -> None:
    host = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    port = int(os.environ.get("EMAIL_PORT", "465"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    to_addr = os.environ.get("EMAIL_TO", user)
    if not user or not password:
        return
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
    except Exception as e:
        print(f"[email] échec: {e}", file=sys.stderr)


def send_whatsapp(message: str) -> None:
    phone = os.environ.get("WHATSAPP_PHONE")
    apikey = os.environ.get("WHATSAPP_APIKEY")
    if not phone or not apikey:
        return
    try:
        requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": message, "apikey": apikey},
            timeout=15,
        )
    except Exception as e:
        print(f"[whatsapp] échec: {e}", file=sys.stderr)


def notify_all(title: str, message: str) -> None:
    send_ntfy(title, message)
    send_email(title, message)
    send_whatsapp(f"{title}\n{message}")


def main() -> None:
    state = load_state()

    if state.get("open_notified"):
        print("Déjà notifié comme ouvert précédemment, rien à faire.")
        return

    text, has_form = fetch_rendered_page()
    current_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    status = determine_status(text, has_form)

    print(f"Statut détecté : {status} (form présent : {has_form})")

    if status == "open":
        notify_all(
            "🚨 Inscriptions ouvertes ! Défilé L'Oréal Paris 2026",
            f"Les inscriptions semblent ouvertes.\n{URL}",
        )
        state["open_notified"] = True
        state["last_hash"] = current_hash
        save_state(state)
        return

    # Filet de sécurité : si le contenu de la page a changé de façon
    # significative mais que la détection par mots-clés n'a rien donné,
    # on prévient quand même (au maximum 2 fois pour éviter le spam).
    if (
        state.get("last_hash")
        and state["last_hash"] != current_hash
        and state.get("change_notices_sent", 0) < 2
    ):
        notify_all(
            "ℹ️ Changement détecté sur la page d'inscription L'Oréal",
            f"Le contenu de la page a changé. Vérifie manuellement si "
            f"les inscriptions sont ouvertes.\n{URL}",
        )
        state["change_notices_sent"] = state.get("change_notices_sent", 0) + 1

    state["last_hash"] = current_hash
    save_state(state)


if __name__ == "__main__":
    main()
