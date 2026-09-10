import json
import re
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
    "Accept": "*/*",
    "X-Livewire": "1",
    "Origin": BASE_URL,
    "Referer": GAMES_URL,
    "Content-Type": "application/json",
}


def clean(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def extract_games(html):
    soup = BeautifulSoup(html, "html.parser")

    games = {}

    for link in soup.find_all("a", href=True):

        href = link["href"].strip()

        if "/game/" not in href:
            continue

        url = urljoin(BASE_URL, href)

        title = clean(
            link.get_text(" ", strip=True)
        )

        if not title:
            image = link.find("img")

            if image:
                title = clean(
                    image.get("alt")
                    or image.get("title")
                    or ""
                )

        if not title:
            continue

        game = {
            "title": title,
            "url": url
        }

        image = link.find("img")

        if image:
            image_url = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
            )

            if image_url:
                game["image"] = urljoin(
                    BASE_URL,
                    image_url
                )

        games[url] = game

    return games


def get_livewire_component(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    component = soup.find(
        attrs={
            "wire:name": "games-list"
        }
    )

    if not component:
        raise RuntimeError(
            "No se encontró el componente games-list"
        )

    snapshot = component.get(
        "wire:snapshot"
    )

    component_id = component.get(
        "wire:id"
    )

    if not snapshot:
        raise RuntimeError(
            "No se encontró wire:snapshot"
        )

    if not component_id:
        raise RuntimeError(
            "No se encontró wire:id"
        )

    return component_id, snapshot


def make_livewire_request(
    session,
    component_id,
    snapshot
):

    payload = {
        "_token": "",
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
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    print(
        "Livewire HTTP:",
        response.status_code
    )

    if response.status_code != 200:

        print(
            "Response:",
            response.text[:2000]
        )

        response.raise_for_status()

    return response.json()


def extract_html_from_livewire(response_json):

    if not isinstance(response_json, dict):
        return None

    components = response_json.get(
        "components"
    )

    if components:

        component = components[0]

        if isinstance(component, dict):

            effects = component.get(
                "effects"
            )

            if isinstance(effects, dict):

                html = effects.get(
                    "html"
                )

                if html:
                    return html

    return None


def main():

    session = requests.Session()

    print(
        "Downloading initial page..."
    )

    response = session.get(
        GAMES_URL,
        headers=HEADERS,
        timeout=60
    )

    print(
        "Initial HTTP:",
        response.status_code
    )

    print(
        "Initial HTML:",
        len(response.text)
    )

    response.raise_for_status()

    # Encontrar juegos iniciales.
    games = extract_games(
        response.text
    )

    print(
        "Initial games:",
        len(games)
    )

    # Obtener componente Livewire.
    component_id, snapshot = (
        get_livewire_component(
            response.text
        )
    )

    print(
        "Component ID:",
        component_id
    )

    # Obtener token CSRF del HTML.
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    token_element = soup.find(
        "meta",
        attrs={"name": "csrf-token"}
    )

    csrf_token = ""

    if token_element:
        csrf_token = (
            token_element.get("content")
            or ""
        )

    print(
        "CSRF token found:",
        bool(csrf_token)
    )

    # Usar el token real.
    HEADERS["X-CSRF-TOKEN"] = csrf_token

    # Insertarlo en el payload posteriormente.
    for request_number in range(1, 101):

        print()
        print(
            f"Loading more "
            f"({request_number}/100)..."
        )

        try:

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

            livewire_response = session.post(
                LIVEWIRE_URL,
                headers=HEADERS,
                json=payload,
                timeout=60
            )

            print(
                "Livewire HTTP:",
                livewire_response.status_code
            )

            if livewire_response.status_code != 200:

                print(
                    "Response:",
                    livewire_response.text[:2000]
                )

                break

            data = livewire_response.json()

            # Extraer HTML actualizado.
            new_html = (
                extract_html_from_livewire(
                    data
                )
            )

            if not new_html:

                print(
                    "No se encontró HTML "
                    "en la respuesta Livewire."
                )

                print(
                    "Response keys:",
                    list(data.keys())
                )

                break

            # Extraer juegos nuevos.
            before = len(games)

            new_games = extract_games(
                new_html
            )

            for url, game in new_games.items():
                games[url] = game

            added = len(games) - before

            print(
                "New games:",
                added
            )

            print(
                "Total games:",
                len(games)
            )

            # Obtener el nuevo snapshot.
            soup = BeautifulSoup(
                new_html,
                "html.parser"
            )

            component = soup.find(
                attrs={
                    "wire:name": "games-list"
                }
            )

            if component:

                new_snapshot = component.get(
                    "wire:snapshot"
                )

                if new_snapshot:

                    snapshot = new_snapshot

            # Si no aparecieron juegos nuevos,
            # probablemente llegamos al final.
            if added == 0:

                print(
                    "No new games found."
                )

                break

        except Exception as error:

            print(
                "Livewire error:",
                repr(error)
            )

            break

    print()
    print("=" * 50)
    print(
        "FINAL TOTAL:",
        len(games)
    )
    print("=" * 50)

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
            key=lambda x:
                x["title"].lower()
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

    print(
        "games.json created successfully."
    )


if __name__ == "__main__":
    main()
