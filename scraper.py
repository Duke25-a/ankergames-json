import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE_URL = "https://ankergames.net"
GAMES_URL = f"{BASE_URL}/games-list"


def clean(value):
    if not value:
        return None

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def extract_games(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    games = {}

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a["href"].strip()

        match = re.match(
            r"^/game/([^/?#]+)",
            href
        )

        if not match:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        title = clean(
            a.get_text(
                " ",
                strip=True
            )
        )

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


def main():

    print("Starting browser...")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            }
        )

        print(
            "Opening:",
            GAMES_URL
        )

        page.goto(
            GAMES_URL,
            wait_until="networkidle",
            timeout=120000
        )

        print(
            "Page loaded."
        )

        games = extract_games(
            page.content()
        )

        print(
            "Initial games:",
            len(games)
        )

        # Intentamos hasta 100 cargas.
        for i in range(100):

            # Buscar botón por texto.
            button = page.get_by_text(
                "Load More Games",
                exact=True
            )

            count = button.count()

            if count == 0:

                print(
                    "Load More Games button "
                    "not found."
                )

                break

            if not button.first.is_visible():

                print(
                    "Load More Games button "
                    "is not visible."
                )

                break

            before = len(games)

            print()
            print(
                f"Loading more "
                f"({i + 1}/100)..."
            )

            try:

                button.first.click(
                    timeout=30000
                )

            except Exception as exc:

                print(
                    "Click error:",
                    exc
                )

                break

            # Esperar a que Livewire termine.
            page.wait_for_timeout(
                2500
            )

            # Extraer todo el DOM actual.
            current = extract_games(
                page.content()
            )

            games.update(
                current
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

            if added == 0:

                print(
                    "No new games."
                )

                break

        browser.close()

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
    ) as f:

        json.dump(
            result,
            f,
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
