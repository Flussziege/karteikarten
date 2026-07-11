from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any
import hmac


import streamlit as st


# ------------------------------------------------------------
# Grundeinstellungen
# ------------------------------------------------------------
st.set_page_config(
    page_title="Karteikarten-Trainer",
    page_icon="🧠",
    layout="centered",
)



def check_password() -> None:
    """Prüft das eingegebene Passwort."""
    entered_password = st.session_state.get("password_input", "")
    correct_password = st.secrets["APP_PASSWORD"]

    if hmac.compare_digest(entered_password, correct_password):
        st.session_state["password_correct"] = True

        # Eingegebenes Passwort aus dem Session State entfernen
        st.session_state.pop("password_input", None)
    else:
        st.session_state["password_correct"] = False


def require_password() -> bool:
    """Zeigt die App erst nach korrekter Passworteingabe an."""

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Geschützter Bereich")
    st.write("Bitte gib das Passwort ein, um die Karteikarten zu öffnen.")

    st.text_input(
        "Passwort",
        type="password",
        key="password_input",
        on_change=check_password,
        autocomplete="current-password",
    )

    if st.session_state.get("password_correct") is False:
        st.error("Das Passwort ist falsch.")

    return False


if not require_password():
    st.stop()




BASE_DIR = Path(__file__).resolve().parent
TOPICS_DIR = BASE_DIR / "topics"


# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            max-width: 920px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .app-title {
            text-align: center;
            margin-bottom: 0.25rem;
        }

        .app-subtitle {
            text-align: center;
            color: #6b7280;
            margin-bottom: 2rem;
        }

        .flashcard-label {
            color: #6b7280;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .flashcard-heading {
            font-size: 1.55rem;
            font-weight: 750;
            line-height: 1.25;
            margin-bottom: 1rem;
        }

        .answer-separator {
            border-top: 1px solid rgba(128, 128, 128, 0.28);
            margin: 1.4rem 0 1.2rem 0;
        }

        div[data-testid="stButton"] > button {
            border-radius: 12px;
            min-height: 2.75rem;
            font-weight: 650;
        }

        div[data-testid="stProgress"] > div > div > div > div {
            border-radius: 99px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Sitzungszustand
# ------------------------------------------------------------
DEFAULT_STATE = {
    "screen": "menu",
    "topic_file": None,
    "topic": None,
    "cards": [],
    "card_index": 0,
    "show_answer": False,
    "shuffle_cards": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ------------------------------------------------------------
# Datei- und Datenfunktionen
# ------------------------------------------------------------
def load_json(path: Path) -> dict[str, Any]:
    """Lädt und prüft eine Themen-Datei."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültiges JSON in '{path.name}' "
            f"(Zeile {exc.lineno}, Spalte {exc.colno})."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"'{path.name}' muss ein JSON-Objekt enthalten.")

    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError(f"'{path.name}' benötigt einen nichtleeren 'title'.")

    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError(f"'{path.name}' benötigt eine nichtleere Liste 'cards'.")

    required_card_keys = {"heading", "question", "answer"}
    for number, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            raise ValueError(
                f"Karte {number} in '{path.name}' muss ein JSON-Objekt sein."
            )

        missing = required_card_keys - card.keys()
        if missing:
            raise ValueError(
                f"Karte {number} in '{path.name}' fehlt: "
                f"{', '.join(sorted(missing))}"
            )

    return data


def discover_topics() -> list[dict[str, Any]]:
    """Findet automatisch alle JSON-Dateien im Ordner topics."""
    topics: list[dict[str, Any]] = []

    if not TOPICS_DIR.exists():
        return topics

    for path in sorted(TOPICS_DIR.glob("*.json")):
        try:
            data = load_json(path)
            topics.append(
                {
                    "path": path,
                    "title": data["title"],
                    "description": data.get("description", ""),
                    "card_count": len(data["cards"]),
                }
            )
        except ValueError as exc:
            topics.append(
                {
                    "path": path,
                    "title": path.stem,
                    "description": "",
                    "card_count": 0,
                    "error": str(exc),
                }
            )

    return topics


def normalize_blocks(content: Any) -> list[dict[str, Any]]:
    """
    Erlaubte Schreibweisen:
    - "Einfacher Text"
    - {"type": "latex", "content": "..."}
    - [{"type": "text", ...}, {"type": "image", ...}]
    """
    if isinstance(content, str):
        return [{"type": "text", "content": content}]

    if isinstance(content, dict):
        return [content]

    if isinstance(content, list):
        return content

    return [
        {
            "type": "text",
            "content": f"Nicht unterstützter Inhalt: {content!r}",
        }
    ]


def resolve_media_path(topic_file: Path, media_path: str) -> Path:
    """Löst Bildpfade relativ zur jeweiligen Themen-Datei auf."""
    path = Path(media_path)

    if path.is_absolute():
        return path

    return (topic_file.parent / path).resolve()


def render_content(content: Any, topic_file: Path) -> None:
    """Zeigt Text, Markdown, LaTeX und Bilder an."""
    for block in normalize_blocks(content):
        if not isinstance(block, dict):
            st.warning(f"Ungültiger Inhaltsblock: {block!r}")
            continue

        block_type = str(block.get("type", "text")).lower()
        value = block.get("content", "")

        if block_type == "text":
            st.write(value)

        elif block_type == "markdown":
            st.markdown(str(value))

        elif block_type == "latex":
            st.latex(str(value))

        elif block_type == "image":
            image_path = resolve_media_path(topic_file, str(value))
            caption = block.get("caption")

            if image_path.exists():
                st.image(
                    str(image_path),
                    caption=caption,
                    use_container_width=True,
                )
            else:
                st.error(f"Bild nicht gefunden: {image_path}")

        else:
            st.warning(f"Unbekannter Inhaltstyp: '{block_type}'")


# ------------------------------------------------------------
# Navigation
# ------------------------------------------------------------
def open_topic(topic_path: Path) -> None:
    topic = load_json(topic_path)
    cards = list(topic["cards"])

    if st.session_state.shuffle_cards:
        random.shuffle(cards)

    st.session_state.topic_file = topic_path
    st.session_state.topic = topic
    st.session_state.cards = cards
    st.session_state.card_index = 0
    st.session_state.show_answer = False
    st.session_state.screen = "cards"


def go_to_menu() -> None:
    st.session_state.screen = "menu"
    st.session_state.topic_file = None
    st.session_state.topic = None
    st.session_state.cards = []
    st.session_state.card_index = 0
    st.session_state.show_answer = False


def previous_card() -> None:
    if st.session_state.card_index > 0:
        st.session_state.card_index -= 1
        st.session_state.show_answer = False


def next_card() -> None:
    if st.session_state.card_index < len(st.session_state.cards) - 1:
        st.session_state.card_index += 1
        st.session_state.show_answer = False


def toggle_answer() -> None:
    st.session_state.show_answer = not st.session_state.show_answer


# ------------------------------------------------------------
# Startmenü
# ------------------------------------------------------------
def render_menu() -> None:
    st.markdown("<h1 class='app-title'>🧠 Karteikarten-Trainer</h1>", unsafe_allow_html=True)
    st.markdown(
        "<div class='app-subtitle'>Wähle ein Thema und lerne Karte für Karte.</div>",
        unsafe_allow_html=True,
    )

    topics = discover_topics()

    if not topics:
        st.error(
            "Es wurden keine Themen gefunden. "
            "Lege mindestens eine JSON-Datei im Ordner 'topics' an."
        )
        return

    st.session_state.shuffle_cards = st.toggle(
        "Karten beim Start mischen",
        value=st.session_state.shuffle_cards,
    )

    st.divider()

    for topic_info in topics:
        with st.container(border=True):
            st.subheader(topic_info["title"])

            if topic_info.get("error"):
                st.error(topic_info["error"])
                continue

            if topic_info["description"]:
                st.write(topic_info["description"])

            st.caption(f"{topic_info['card_count']} Karte(n)")

            if st.button(
                "Thema öffnen",
                key=f"open_{topic_info['path'].name}",
                use_container_width=True,
                type="primary",
            ):
                open_topic(topic_info["path"])
                st.rerun()


# ------------------------------------------------------------
# Karteikartenansicht
# ------------------------------------------------------------
def render_card_screen() -> None:
    topic = st.session_state.topic
    topic_file = st.session_state.topic_file
    cards = st.session_state.cards
    index = st.session_state.card_index

    if not topic or not topic_file or not cards:
        go_to_menu()
        st.rerun()

    current_card = cards[index]
    total = len(cards)

    top_left, top_right = st.columns([1, 3])

    with top_left:
        if st.button("← Startmenü", use_container_width=True):
            go_to_menu()
            st.rerun()

    with top_right:
        st.markdown(f"### {topic['title']}")

    st.progress((index + 1) / total)
    st.caption(f"Karte {index + 1} von {total}")

    with st.container(border=True):
        st.markdown(
            "<div class='flashcard-label'>Frage</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='flashcard-heading'>{current_card['heading']}</div>",
            unsafe_allow_html=True,
        )

        render_content(current_card["question"], topic_file)

        if st.session_state.show_answer:
            st.markdown(
                "<div class='answer-separator'></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='flashcard-label'>Antwort</div>",
                unsafe_allow_html=True,
            )
            render_content(current_card["answer"], topic_file)

        flip_label = (
            "Antwort ausblenden"
            if st.session_state.show_answer
            else "Karte umdrehen – Antwort anzeigen"
        )

        if st.button(
            flip_label,
            key=f"flip_{index}",
            use_container_width=True,
            type="primary",
        ):
            toggle_answer()
            st.rerun()

    st.write("")

    previous_col, counter_col, next_col = st.columns([1, 1, 1])

    with previous_col:
        if st.button(
            "← Zurück",
            use_container_width=True,
            disabled=index == 0,
        ):
            previous_card()
            st.rerun()

    with counter_col:
        st.markdown(
            f"<div style='text-align:center; padding-top:0.7rem;'>"
            f"{index + 1} / {total}</div>",
            unsafe_allow_html=True,
        )

    with next_col:
        if st.button(
            "Weiter →",
            use_container_width=True,
            disabled=index == total - 1,
        ):
            next_card()
            st.rerun()


# ------------------------------------------------------------
# App starten
# ------------------------------------------------------------
if st.session_state.screen == "menu":
    render_menu()
else:
    render_card_screen()
