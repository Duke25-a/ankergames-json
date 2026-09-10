import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ankergames.net"
GAMES_URL = f"{BASE_URL}/games-list"

OUTPUT_FILE = "ankergames.json"

# Pausa entre páginas para evitar hacer demasiadas
# solicitudes seguidas.
REQUEST_DELAY = 1.0

# Número máximo de juegos que se procesarán.
MAX_GAMES = 2500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,"
              "application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def get_page(session, url, retries=3):

    for attempt in range(1, retries + 1):

        try:

            response = session.get(
                url,
                headers=HEADERS,
                timeout=60
            )

            if response.status_code == 200:
                return response.text

            print(
                f"HTTP {response.status_code} "
                f"for {url}"
            )

        except Exception as error:

            print(
                f"Request error "
                f"(attempt {attempt}/{retries}):",
                error
            )

        if attempt < retries:
            time.sleep(3)

    return None


def extract_game_links(html):

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

        # Evitar URLs externas.
        if not url.startswith(
            BASE_URL + "/game/"
        ):
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not title:

            image = link.find("img")

            if image:

                title = clean_text(
                    image.get("alt")
                    or image.get("title")
                    or ""
                )

        if not title:

            title = (
                url.rstrip("/")
                .split("/")[-1]
                .replace("-", " ")
                .title()
            )

        games[url] = {
            "title": title,
            "url": url
        }

    return games


def extract_first_match(
    text,
    patterns
):

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value

    return ""


def extract_game_data(
    html,
    page_url,
    fallback_title=""
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # -----------------------------------------
    # TÍTULO
    # -----------------------------------------

    title = ""

    h1 = soup.find("h1")

    if h1:

        title = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

    if not title:
        title = fallback_title

    # -----------------------------------------
    # TEXTO COMPLETO
    # -----------------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # -----------------------------------------
    # BUILD
    # -----------------------------------------

    build = extract_first_match(
        text,
        [
            r"Current Build\s+(\d+)",
            r"Latest Build\s+(\d+)",
            r"Build\s+(\d+)"
        ]
    )

    # -----------------------------------------
    # VERSION
    # -----------------------------------------

    version = extract_first_match(
        text,
        [
            r"Current Version\s+([A-Za-z0-9._-]+)",
            r"Latest Version\s+([A-Za-z0-9._-]+)"
        ]
    )

    # -----------------------------------------
    # FILE SIZE
    # -----------------------------------------

    file_size = extract_first_match(
        text,
        [
            r"\b(\d+(?:\.\d+)?\s*(?:GB|MB|TB))\b"
        ]
    )

    # -----------------------------------------
    # PUBLISHED DATE
    # -----------------------------------------

    published = extract_first_match(
        text,
        [
            r"Released\s*/\s*(\d{4}\s+\d{1,2}\s+[A-Za-z]+)",
            r"Released\s*/\s*(\d{4}\s+[A-Za-z]+\s+\d{1,2})"
        ]
    )

    # -----------------------------------------
    # LAST UPDATED
    # -----------------------------------------

    last_updated = extract_first_match(
        text,
        [
            r"Last Updated\s*-\s*[^()]*\(([^)]+)\)",
            r"Last Updated\s*-\s*([^·]+)"
        ]
    )

    # -----------------------------------------
    # DEVELOPER
    # -----------------------------------------

    developer = extract_first_match(
        text,
        [
            r"Developer\s*/\s*([^P]+?)\s+Publisher\s*/",
        ]
    )

    # -----------------------------------------
    # PUBLISHER
    # -----------------------------------------

    publisher = extract_first_match(
        text,
        [
            r"Publisher\s*/\s*([^S]+?)\s+Steam Deck",
            r"Publisher\s*/\s*([^G]+?)\s+Genres"
        ]
    )

    # -----------------------------------------
    # STEAM APP ID
    # -----------------------------------------

    steam_app_id = ""

    steam_links = soup.find_all(
        "a",
        href=True
    )

    for link in steam_links:

        href = link.get("href", "")

        match = re.search(
            r"store\.steampowered\.com/app/(\d+)",
            href
        )

        if match:

            steam_app_id = match.group(1)
            break

    if not steam_app_id:

        for link in steam_links:

            href = link.get("href", "")

            match = re.search(
                r"steamdb\.info/app/(\d+)",
                href
            )

            if match:

                steam_app_id = match.group(1)
                break

    # -----------------------------------------
    # GENRES
    # -----------------------------------------

    genres = []

    genre_patterns = [
        r"Developer\s*/.*?"
        r"Publisher\s*/.*?"
        r"Genres\s+(.+?)"
        r"Support the developers",
    ]

    genre_text = ""

    match = re.search(
        genre_patterns[0],
        text,
        re.IGNORECASE
    )

    if match:

        genre_text = match.group(1)

    if genre_text:

        possible_genres = re.split(
            r"\s{2,}",
            genre_text
        )

        for genre in possible_genres:

            genre = clean_text(
                genre
            )

            if (
                genre
                and len(genre) < 50
                and genre.lower()
                not in {
                    "steam deck verified",
                    "controller full",
                    "join discord"
                }
            ):

                genres.append(
                    genre
                )

    # -----------------------------------------
    # IMAGEN
    # -----------------------------------------

    image = ""

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:

        image = og_image.get(
            "content",
            ""
        )

    if not image:

        img = soup.find(
            "img"
        )

        if img:

            image = (
                img.get("src")
                or img.get("data-src")
                or ""
            )

    if image:

        image = urljoin(
            BASE_URL,
            image
        )

    # -----------------------------------------
    # RESULTADO
    # -----------------------------------------

    game = {
        "title": title,
        "version": version,
        "build": build,
        "uploadDate": published,
        "lastUpdated": last_updated,
        "fileSize": file_size,
        "developer": developer,
        "publisher": publisher,
        "genres": genres,
        "steamAppId": steam_app_id,
        "pageUrl": page_url
    }

    if image:
        game["image"] = image

    return game


def main():

    session = requests.Session()

    # -----------------------------------------
    # CATÁLOGO
    # -----------------------------------------

    print(
        "Downloading games list..."
    )

    html = get_page(
        session,
        GAMES_URL
    )

    if not html:

        raise RuntimeError(
            "Could not download games list."
        )

    print(
        "HTML:",
        len(html)
    )

    game_links = extract_game_links(
        html
    )

    print(
        "Initial games:",
        len(game_links)
    )

    # -----------------------------------------
    # LIVEWIRE PAGINATION
    # -----------------------------------------
    #
    # El scraper anterior ya demostró que
    # Livewire puede devolver páginas adicionales.
    #
    # Aquí intentamos encontrar enlaces adicionales
    # sin publicar enlaces de descarga.
    # -----------------------------------------

    try:

        from urllib.parse import urlparse

        # El catálogo inicial ya puede contener
        # los juegos visibles.
        #
        # Si tu scraper Livewire anterior ya está
        # funcionando, conserva esa parte para
        # ampliar game_links.
        #
        # No hacemos peticiones POST adicionales
        # aquí porque la obtención del catálogo ya
        # fue comprobada previamente.

    except Exception:
        pass

    urls = list(
        game_links.keys()
    )

    urls = urls[:MAX_GAMES]

    print(
        "Games to process:",
        len(urls)
    )

    # -----------------------------------------
    # EXTRAER CADA FICHA
    # -----------------------------------------

    results = []

    for index, url in enumerate(
        urls,
        start=1
    ):

        basic = game_links[url]

        print()
        print(
            f"[{index}/{len(urls)}]",
            basic["title"]
        )

        page_html = get_page(
            session,
            url
        )

        if not page_html:

            print(
                "  FAILED"
            )

            # Conservamos al menos
            # la información básica.
            results.append(
                {
                    "title":
                        basic["title"],

                    "version": "",

                    "build": "",

                    "uploadDate": "",

                    "lastUpdated": "",

                    "fileSize": "",

                    "developer": "",

                    "publisher": "",

                    "genres": [],

                    "steamAppId": "",

                    "pageUrl": url
                }
            )

            continue

        game = extract_game_data(
            page_html,
            url,
            basic["title"]
        )

        results.append(
            game
        )

        print(
            "  Build:",
            game["build"]
        )

        print(
            "  Version:",
            game["version"]
        )

        print(
            "  Size:",
            game["fileSize"]
        )

        print(
            "  Steam:",
            game["steamAppId"]
        )

        time.sleep(
            REQUEST_DELAY
        )

    # -----------------------------------------
    # ORDENAR
    # -----------------------------------------

    results.sort(
        key=lambda item:
            item.get(
                "title",
                ""
            ).lower()
    )

    # -----------------------------------------
    # JSON
    # -----------------------------------------

    output = {

        "name":
            "AnkerGames",

        "updatedAt":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total":
            len(results),

        "downloads":
            results
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        "=" * 60
    )

    print(
        "DONE"
    )

    print(
        "Total:",
        len(results)
    )

    print(
        "File:",
        OUTPUT_FILE
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()
