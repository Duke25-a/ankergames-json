import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ankergames.net"
GAMES_URL = f"{BASE_URL}/games-list"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
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

    # Buscar cualquier enlace que contenga /game/
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

        # Intentar obtener título desde imagen
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

    return list(games.values())


def main():

    print(
        "Downloading initial page..."
    )

    response = requests.get(
        GAMES_URL,
        headers=HEADERS,
        timeout=60
    )

    print(
        "HTTP:",
        response.status_code
    )

    print(
        "Downloaded:",
        len(response.text),
        "bytes"
    )

    response.raise_for_status()

    games = extract_games(
        response.text
    )

    print(
        "Games found:",
        len(games)
    )

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
            games,
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
