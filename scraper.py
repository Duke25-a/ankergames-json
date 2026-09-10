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
    """
    Extrae los juegos encontrados en un fragmento HTML.
    """

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

        # Intentar encontrar el título
        title = clean(
            link.get_text(
                " ",
                strip=True
            )
        )

        # Si no hay texto, buscarlo en la imagen
        if not title:

            image = link.find("img")

            if image:

                title = clean(
                    image.get("alt")
                    or image.get("title")
                    or ""
                )

        # Si seguimos sin título, guardar igualmente
        # la URL para poder analizarla.
        if not title:
            title = url.rstrip("/").split("/")[-1]

        game = {
            "title": title,
            "url": url
        }

        # Buscar imagen
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
            "No se encontró el componente "
            "Livewire games-list"
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


def extract_csrf_token(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Método 1: meta csrf-token
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

    # Método 2: input _token
    input_token = soup.find(
        "input",
        attrs={
            "name": "_token"
        }
    )

    if input_token:

        token = input_token.get(
            "value"
        )

        if token:
            return token

    # Método 3: buscar _token en scripts/HTML
    match = re.search(
        r'"_token"\s*:\s*"([^"]+)"',
        html
    )

    if match:
        return match.group(1)

    return ""


def extract_livewire_html(data):

    """
    Livewire normalmente devuelve el HTML actualizado
    dentro de effects.html.
    """

    if not isinstance(
        data,
        dict
    ):
        return None

    components = data.get(
        "components"
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

    html = effects.get(
        "html"
    )

    return html


def extract_new_snapshot(html):

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
        return None

    return component.get(
        "wire:snapshot"
    )


def print_game_links(
    html,
    maximum=35
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/game/" not in href:
            continue

        href = urljoin(
            BASE_URL,
            href
        )

        if href not in links:
            links.append(href)

    print(
        "Game links returned by Livewire:",
        len(links)
    )

    for link in links[:maximum]:

        print(
            "  ",
            link
        )


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

    # --------------------------------------------------
    # JUEGOS INICIALES
    # --------------------------------------------------

    games = extract_games(
        response.text
    )

    print(
        "Initial games:",
        len(games)
    )

    # --------------------------------------------------
    # LIVEWIRE COMPONENT
    # --------------------------------------------------

    component_id, snapshot = (
        get_livewire_component(
            response.text
        )
    )

    print(
        "Component ID:",
        component_id
    )

    # --------------------------------------------------
    # CSRF
    # --------------------------------------------------

    csrf_token = extract_csrf_token(
        response.text
    )

    print(
        "CSRF token found:",
        bool(csrf_token)
    )

    if csrf_token:

        HEADERS[
            "X-CSRF-TOKEN"
        ] = csrf_token

    # --------------------------------------------------
    # PAGINACIÓN LIVEWIRE
    # --------------------------------------------------

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

            "_token": csrf_token,

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

            livewire_response = session.post(
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
            livewire_response.status_code
        )

        # --------------------------------------------------
        # ERROR HTTP
        # --------------------------------------------------

        if livewire_response.status_code != 200:

            print(
                "Response:"
            )

            print(
                livewire_response.text[:3000]
            )

            break

        # --------------------------------------------------
        # JSON
        # --------------------------------------------------

        try:

            data = livewire_response.json()

        except Exception as error:

            print(
                "JSON error:",
                repr(error)
            )

            print(
                livewire_response.text[:3000]
            )

            break

        print(
            "Response keys:",
            list(data.keys())
        )

        # --------------------------------------------------
        # HTML DEVUELTO
        # --------------------------------------------------

        new_html = extract_livewire_html(
            data
        )

        if not new_html:

            print(
                "No se encontró effects.html"
            )

            print(
                "Full response:"
            )

            print(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2
                )[:5000]
            )

            break

        print(
            "Returned HTML:",
            len(new_html),
            "bytes"
        )

        # --------------------------------------------------
        # INSPECCIÓN
        # --------------------------------------------------

        soup = BeautifulSoup(
            new_html,
            "html.parser"
        )

        all_links = soup.find_all(
            "a",
            href=True
        )

        print(
            "Links returned by Livewire:",
            len(all_links)
        )

        print_game_links(
            new_html
        )

        # --------------------------------------------------
        # EXTRAER JUEGOS
        # --------------------------------------------------

        before = len(games)

        new_games = extract_games(
            new_html
        )

        print(
            "Games extracted from response:",
            len(new_games)
        )

        for url, game in new_games.items():

            games[url] = game

        added = len(games) - before

        print(
            "New games added:",
            added
        )

        print(
            "Total games:",
            len(games)
        )

        # --------------------------------------------------
        # ACTUALIZAR SNAPSHOT
        # --------------------------------------------------

        new_snapshot = extract_new_snapshot(
            new_html
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

        # --------------------------------------------------
        # FINAL
        # --------------------------------------------------

        if added == 0:

            print()
            print(
                "No new games found."
            )

            # No terminamos inmediatamente.
            # Guardamos información para analizar
            # qué está ocurriendo.

            break

    # ------------------------------------------------------
    # RESULTADO FINAL
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # JSON
    # ------------------------------------------------------

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
