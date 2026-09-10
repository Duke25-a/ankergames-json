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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


def clean(value):
    if not value:
        return None
    return re.sub(r"\s+", " ", str(value)).strip()


def get_page(session):
    response = session.get(
        GAMES_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def find_livewire_component(html):
    soup = BeautifulSoup(html, "html.parser")

    # Livewire 3/4 normalmente coloca el snapshot
    # en wire:snapshot.
    element = soup.find(attrs={"wire:snapshot": True})

    if element:
        snapshot = element.get("wire:snapshot")
        component_id = element.get("wire:id")

        return snapshot, component_id

    # Compatibilidad con versiones/variantes que usan wire:initial-data
    element = soup.find(attrs={"wire:initial-data": True})

    if element:
        return element.get("wire:initial-data"), element.get("wire:id")

    return None, None


def extract_games_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    games = {}

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not re.match(r"^/game/[^/]+/?$", href):
            continue

        url = urljoin(BASE_URL, href)

        title = clean(a.get_text(" ", strip=True))

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
                game["image"] = urljoin(BASE_URL, src)

        games[url] = game

    return games


def extract_games_from_response(data):
    """
    Livewire devuelve efectos HTML.
    Intentamos localizar HTML nuevo dentro
    de los efectos de la respuesta.
    """

    games = {}

    if not isinstance(data, dict):
        return games

    components = data.get("components", [])

    for component in components:

        effects = component.get("effects", {})

        html = effects.get("html")

        if html:
            found = extract_games_from_html(html)
            games.update(found)

    return games


def load_more(session, snapshot, component_id):
    payload = {
        "_token": None,
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

    response = session.post(
        LIVEWIRE_URL,
        headers={
            **HEADERS,
            "Accept": "*/*",
            "Content-Type": "application/json",
            "X-Livewire": "1",
            "Referer": GAMES_URL,
            "Origin": BASE_URL
        },
        json=payload,
        timeout=30
    )

    print("Livewire HTTP:", response.status_code)

    response.raise_for_status()

    return response.json()


def parse_livewire_response(data):
    games = extract_games_from_response(data)

    new_snapshot = None

    components = data.get("components", [])

    for component in components:
        new_snapshot = component.get("snapshot")

        if new_snapshot:
            break

    return games, new_snapshot


def main():

    session = requests.Session()

    print("Downloading initial page...")

    html = get_page(session)

    print("Initial HTML:", len(html), "bytes")

    games = extract_games_from_html(html)

    print("Initial games:", len(games))

    snapshot, component_id = find_livewire_component(html)

    if not snapshot:
        raise RuntimeError(
            "Could not find Livewire snapshot."
        )

    print("Livewire snapshot found.")

    print("Component ID:", component_id)

    # Repetimos hasta que Livewire deje de devolver juegos.
    max_requests = 100

    for i in range(max_requests):

        print()
        print(
            f"Loading more games "
            f"(request {i + 1}/{max_requests})..."
        )

        try:

            data = load_more(
                session,
                snapshot,
                component_id
            )

        except Exception as exc:

            print("Livewire error:", exc)
            break

        new_games, new_snapshot = parse_livewire_response(data)

        before = len(games)

        games.update(new_games)

        added = len(games) - before

        print("New games:", added)
        print("Total games:", len(games))

        if new_snapshot:
            snapshot = new_snapshot

        if added == 0:
            print(
                "No more games returned. "
                "Stopping."
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
            key=lambda x: x["title"].lower()
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
    print(f"FINAL TOTAL: {len(games)}")
    print("games.json created.")
    print("=" * 50)


if __name__ == "__main__":
    main()
