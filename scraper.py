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
    "Accept-Language": "en-US,en;q=0.9",
    "X-Livewire": "1",
    "Origin": BASE_URL,
    "Referer": GAMES_URL,
    "Content-Type": "application/json",
}


def clean(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def extract_games(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    games = {}

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"].strip()

        if "/game/" not in href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        title = clean(
            link.get_text(
                " ",
                strip=True
            )
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

            title = (
                url.rstrip("/")
                .split("/")[-1]
            )

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


def find_component(html):

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
            "No se encontró games-list"
        )

    component_id = component.get(
        "wire:id"
    )

    snapshot = component.get(
        "wire:snapshot"
    )

    if not component_id:

        raise RuntimeError(
            "No se encontró wire:id"
        )

    if not snapshot:

        raise RuntimeError(
            "No se encontró wire:snapshot"
        )

    return component_id, snapshot


def get_csrf(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    meta = soup.find(
        "meta",
        attrs={
            "name": "csrf-token"
        }
    )

    if meta:

        token = meta.get(
            "content"
        )

        if token:
            return token

    token_input = soup.find(
        "input",
        attrs={
            "name": "_token"
        }
    )

    if token_input:

        token = token_input.get(
            "value"
        )

        if token:
            return token

    match = re.search(
        r'"_token"\s*:\s*"([^"]+)"',
        html
    )

    if match:

        return match.group(1)

    return ""


def inspect_response(data):

    print()
    print(
        "Livewire response structure:"
    )

    if not isinstance(
        data,
        dict
    ):

        print(
            "Response is not a dictionary"
        )

        return

    components = data.get(
        "components"
    )

    if not components:

        print(
            "No components found"
        )

        return

    print(
        "Components:",
        len(components)
    )

    for index, component in enumerate(
        components
    ):

        print()
        print(
            f"Component {index}"
        )

        if not isinstance(
            component,
            dict
        ):

            print(
                "Not a dictionary"
            )

            continue

        print(
            "Keys:",
            list(component.keys())
        )

        print(
            "Snapshot:",
            bool(
                component.get(
                    "snapshot"
                )
            )
        )

        print(
            "Effects:",
            bool(
                component.get(
                    "effects"
                )
            )
        )

        snapshot = component.get(
            "snapshot"
        )

        if snapshot:

            print(
                "Snapshot length:",
                len(snapshot)
            )

            try:

                snapshot_data = json.loads(
                    snapshot
                )

                data_section = (
                    snapshot_data.get(
                        "data",
                        {}
                    )
                )

                paginators = (
                    data_section.get(
                        "paginators"
                    )
                )

                print(
                    "Paginators:",
                    paginators
                )

            except Exception:

                print(
                    "Could not decode snapshot"
                )


def get_html_from_response(data):

    components = data.get(
        "components",
        []
    )

    if not components:
        return None

    component = components[0]

    if not isinstance(
        component,
        dict
    ):
        return None

    effects = component.get(
        "effects"
    )

    if not isinstance(
        effects,
        dict
    ):
        return None

    return effects.get(
        "html"
    )


def get_snapshot_from_response(data):

    components = data.get(
        "components",
        []
    )

    if not components:
        return None

    component = components[0]

    if not isinstance(
        component,
        dict
    ):
        return None

    snapshot = component.get(
        "snapshot"
    )

    if snapshot:

        return snapshot

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

    # -----------------------------------------
    # JUEGOS INICIALES
    # -----------------------------------------

    games = extract_games(
        response.text
    )

    print(
        "Initial games:",
        len(games)
    )

    # -----------------------------------------
    # LIVEWIRE
    # -----------------------------------------

    component_id, snapshot = (
        find_component(
            response.text
        )
    )

    print(
        "Component ID:",
        component_id
    )

    # -----------------------------------------
    # CSRF
    # -----------------------------------------

    csrf = get_csrf(
        response.text
    )

    print(
        "CSRF token found:",
        bool(csrf)
    )

    if csrf:

        HEADERS[
            "X-CSRF-TOKEN"
        ] = csrf

    # -----------------------------------------
    # LOAD MORE
    # -----------------------------------------

    for request_number in range(
        1,
        101
    ):

        print()
        print(
            "=" * 60
        )

        print(
            f"Loading more "
            f"({request_number}/100)..."
        )

        print(
            "=" * 60
        )

        payload = {

            "_token": csrf,

            "components": [

                {

                    "snapshot": snapshot,

                    "updates": {},

                    "calls": [

                        {

                            "method":
                                "loadMoreGames",

                            "params": [],

                            "metadata": {}

                        }

                    ]

                }

            ]

        }

        try:

            lw = session.post(
                LIVEWIRE_URL,
                headers=HEADERS,
                json=payload,
                timeout=60
            )

        except Exception as error:

            print(
                "Request error:",
                repr(error)
            )

            break

        print(
            "Livewire HTTP:",
            lw.status_code
        )

        if lw.status_code != 200:

            print(
                lw.text[:3000]
            )

            break

        try:

            data = lw.json()

        except Exception as error:

            print(
                "JSON error:",
                repr(error)
            )

            print(
                lw.text[:3000]
            )

            break

        # -----------------------------------------
        # INSPECCIÓN
        # -----------------------------------------

        inspect_response(
            data
        )

        # -----------------------------------------
        # HTML
        # -----------------------------------------

        new_html = get_html_from_response(
            data
        )

        if not new_html:

            print(
                "No effects.html found."
            )

            break

        print(
            "Returned HTML:",
            len(new_html),
            "bytes"
        )

        # -----------------------------------------
        # JUEGOS
        # -----------------------------------------

        new_games = extract_games(
            new_html
        )

        before = len(games)

        for url, game in new_games.items():

            games[url] = game

        added = len(games) - before

        print(
            "Games in response:",
            len(new_games)
        )

        print(
            "New games:",
            added
        )

        print(
            "Total games:",
            len(games)
        )

        # -----------------------------------------
        # SNAPSHOT NUEVO
        # -----------------------------------------

        new_snapshot = (
            get_snapshot_from_response(
                data
            )
        )

        if new_snapshot:

            snapshot = new_snapshot

            print(
                "Snapshot updated: True"
            )

        else:

            print(
                "Snapshot updated: False"
            )

            print(
                "Cannot continue pagination "
                "without a new snapshot."
            )

            break

        # -----------------------------------------
        # COMPROBAR PÁGINA
        # -----------------------------------------

        try:

            snapshot_data = json.loads(
                snapshot
            )

            current_data = (
                snapshot_data.get(
                    "data",
                    {}
                )
            )

            paginators = (
                current_data.get(
                    "paginators"
                )
            )

            print(
                "Current paginator:",
                paginators
            )

        except Exception:

            pass

        # -----------------------------------------
        # FIN
        # -----------------------------------------

        if added == 0:

            print(
                "No new games found."
            )

            break

    # -----------------------------------------
    # RESULTADO
    # -----------------------------------------

    print()
    print(
        "=" * 50
    )

    print(
        "FINAL TOTAL:",
        len(games)
    )

    print(
        "=" * 50
    )

    result = {

        "source": {

            "name":
                "AnkerGames",

            "url":
                BASE_URL,

            "catalog_url":
                GAMES_URL,

            "updated_at":
                datetime.now(
                    timezone.utc
                ).isoformat()

        },

        "total":
            len(games),

        "games":
            sorted(
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

    print(
        "games.json created successfully."
    )


if __name__ == "__main__":

    main()
