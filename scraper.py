import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ankergames.net"
URL = f"{BASE_URL}/games-list"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
}


def clean(value):
    if not value:
        return None
    return re.sub(r"\s+", " ", value).strip()


def main():
    print("Downloading:", URL)

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("HTTP:", response.status_code)
    print("Downloaded:", len(response.text), "bytes")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    games = []

    # Buscar todos los enlaces que parezcan fichas de juegos.
    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if "/game/" not in href:
            continue

        url = urljoin(BASE_URL, href)

        title = clean(a.get_text(" ", strip=True))

        if not title:
            # Intentar obtener el título desde una imagen
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

        # Imagen
        img = a.find("img")

        if img:
            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if src:
                game["image"] = urljoin(BASE_URL, src)

        games.append(game)

    # Eliminar duplicados
    unique = {}

    for game in games:
        unique[game["url"]] = game

    games = list(unique.values())

    games.sort(
        key=lambda x: x["title"].lower()
    )

    output = {
        "source": {
            "name": "AnkerGames",
            "url": BASE_URL,
            "catalog_url": URL,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat()
        },
        "total": len(games),
        "games": games
    }

    with open(
        "games.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Games found:", len(games))
    print("games.json created successfully.")


if __name__ == "__main__":
    main()
