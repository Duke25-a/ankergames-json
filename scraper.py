import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ankergames.net"
GAMES_URL = f"{BASE_URL}/games-list"
LIVEWIRE_URL = f"{BASE_URL}/livewire-be923db6/update"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    )
}


def clean(value):
    if not value:
        return None

    return re.sub(r"\s+", " ", str(value)).strip()


def get_initial_page(session):
    response = session.get(
        GAMES_URL,
        headers=HEADERS,
        timeout=30
    )

    print("Initial HTTP:", response.status_code)
    print("Initial HTML:", len(response.text), "bytes")

    response.raise_for_status()

    return response.text


def find_csrf_token(soup):
    # Laravel normalmente proporciona el token aquí.
    meta = soup.find(
        "meta",
        attrs={"name": "csrf-token"}
    )

    if meta and meta.get("content"):
        return meta["content"]

    # Fallback: input hidden
    token_input = soup.find(
        "input",
        attrs={"name": "_token"}
    )

    if token_input and token_input.get("value"):
        return token_input["value"]

    return None


def find_livewire_component(soup):
    element = soup.find(
        attrs={"wire:snapshot": True}
    )

    if not element:
        return None, None

    return (
        element.get("wire:snapshot"),
        element.get("wire:id")
    )


def extract_games(soup):
    games = {}

    # Buscar /game/ independientemente de la
    # estructura exacta de la tarjeta.
    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        match = re.search(
            r"^/game/([^/?#]+)",
            href
        )

        if not match:
            continue

        url = urljoin(BASE_URL, href)

        title = clean(
            a.get_text(" ", strip=True)
        )

        # Si el enlace no tiene texto, utilizar alt/title.
        if not title:

            img = a.find("img")

            if img:
                title = clean(
                    img.get("alt")
                    or img.get("title")
                )

        if not title:
            continue

        game = {
            "title": title,
            "url": url
        }

        img = a.find("img")

        if img:

            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if src:
                game["image"] = urljoin(
                    BASE_URL,
                    src
                )

        games[url] = game

    return games


def load_more(
    session,
    snapshot,
    csrf_token
):

    payload = {
        "_token": csrf_token,
        "components": [
            {
                "snapshot": snapshot,
                "updates": {},
                "calls": [
                    {
                        "method": "loadMoreGames",
                        "params": [],
                        "metadata": {}
                    }
                ]
            }
        ]
    }

    headers = {
        **HEADERS,
        "Accept": "*/*",
        "Content-Type": "application/json",
        "X-Livewire": "1",
        "Referer": GAMES_URL,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest"
    }

    response = session.post(
        LIVEWIRE_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(
        "Livewire HTTP:",
        response.status_code
    )

    if response.status_code != 200:

        print(
            "Response:",
            response.text[:500]
        )

    response.raise_for_status()

    return response.json()


def parse_response(data):

    games = {}
    new_snapshot = None

    if not isinstance(data, dict):
        return games, new_snapshot

    components = data.get(
        "components",
        []
    )

    for component in components:

        effects = component.get(
            "effects",
            {}
        )

        html = effects.get("html")

        if html:

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            found = extract_games(
                soup
            )

            games.update(found)

        if component.get("snapshot"):
            new_snapshot = component[
                "snapshot"
            ]

    return games, new_snapshot


def main():

    session = requests.Session()

    print("Downloading initial page...")

    html = get_initial_page(session)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    csrf_token = find_csrf_token(
        soup
    )

    print(
        "CSRF token found:",
        bool(csrf_token)
    )

    if not csrf_token:

        raise RuntimeError(
            "CSRF token was not found."
        )

    snapshot, component_id = (
        find_livewire_component(soup)
    )

    print(
        "Livewire snapshot found:",
        bool(snapshot)
    )

    print(
        "Component ID:",
        component_id
    )

    if not snapshot:

        raise RuntimeError(
            "Livewire snapshot was not found."
        )

    games = extract_games(soup)

    print(
        "Initial games:",
        len(games)
    )

    max_requests = 100

    for number in range(
        max_requests
    ):

        print()
        print(
            f"Loading more "
            f"({number + 1}/{max_requests})..."
        )

        try:

            data = load_more(
                session,
                snapshot,
                csrf_token
            )

            new_games, new_snapshot = (
                parse_response(data)
            )

        except Exception as exc:

            print(
                "Livewire error:",
                exc
            )

            break

        before = len(games)

        games.update(
            new_games
        )

        added = (
            len(games) - before
        )

        print(
            "New games:",
            added
        )

        print(
            "Total games:",
            len(games)
        )

        if new_snapshot:
            snapshot = new_snapshot

        if added == 0:

            print(
                "No new games returned."
            )

            break

        time.sleep(1)

    result = {
        "source": {
            "name": "AnkerGames",
            "url": BASE_URL,
            "catalog_url": GAMES_URL,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat()
        },
        "total": len(games),
        "games": sorted(
            games.values(),
            key=lambda game:
                game["title"].lower()
        )
    }

    with open(
        "games.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 50)
    print(
        "FINAL TOTAL:",
        len(games)
    )
    print(
        "games.json created."
    )
    print("=" * 50)


if __name__ == "__main__":
    main()
