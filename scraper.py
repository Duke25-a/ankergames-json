import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ankergames.net"
GAMES_URL = f"{BASE_URL}/games-list"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AnkerGamesMetadataIndexer/1.0; "
        "+https://github.com/Duke25-a/ankergames-json)"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def clean(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()


def get_soup(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_game_links(soup):
    """
    Obtiene las fichas /game/... visibles en la página.
    """
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if href.startswith("/game/"):
            links.add(urljoin(BASE_URL, href))

    return sorted(links)


def extract_listing_game_data(soup):
    """
    Extrae datos básicos de las tarjetas que aparecen
    en /games-list.
    """
    games = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if not href.startswith("/game/"):
            continue

        url = urljoin(BASE_URL, href)

        title = clean(a.get_text(" ", strip=True))

        if not title:
            continue

        parent = a.parent

        # Intentamos localizar la tarjeta contenedora.
        card = parent

        for _ in range(5):
            if card and card.name in ("article", "li"):
                break

            if card and card.parent:
                card = card.parent

        text = clean(card.get_text(" ", strip=True)) if card else title

        games[url] = {
            "title": title,
            "url": url,
            "listing_text": text
        }

    return games


def parse_detail_page(url):
    """
    Extrae únicamente metadatos públicos de la ficha.
    No extrae enlaces de descarga.
    """

    soup = get_soup(url)

    result = {
        "url": url,
        "title": None,
        "platform": None,
        "size": None,
        "release_year": None,
        "version": None,
        "current_build": None,
        "steam_update": None,
        "description": None,
        "developer": None,
        "publisher": None,
        "genres": [],
        "image": None,
        "steamdb_url": None
    }

    h1 = soup.find("h1")

    if h1:
        result["title"] = clean(h1.get_text(" ", strip=True))

    # Imagen principal
    for img in soup.find_all("img"):
        alt = clean(img.get("alt"))

        if (
            alt
            and result["title"]
            and result["title"].lower() in alt.lower()
        ):
            src = img.get("src") or img.get("data-src")

            if src:
                result["image"] = urljoin(BASE_URL, src)
                break

    # Extraer texto de la página
    text = clean(soup.get_text(" ", strip=True))

    # Plataforma
    platform_match = re.search(
        r"\b(PC|MAC|EMU|APP)\b",
        text,
        re.IGNORECASE
    )

    if platform_match:
        result["platform"] = platform_match.group(1).upper()

    # Tamaño
    size_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(GB|MB)\b",
        text,
        re.IGNORECASE
    )

    if size_match:
        result["size"] = f"{size_match.group(1)} {size_match.group(2)}"

    # Año
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)

    if years:
        # Preferimos años de lanzamiento conocidos
        for year in years:
            y = int(year)
            if 1970 <= y <= 2035:
                result["release_year"] = y
                break

    # Versión
    version_match = re.search(
        r"\b(?:V|B)\s*[\dA-Za-z._-]+",
        text
    )

    if version_match:
        result["version"] = version_match.group(0)

    # Build
    build_match = re.search(
        r"Current Build\s+([0-9]+)",
        text,
        re.IGNORECASE
    )

    if build_match:
        result["current_build"] = build_match.group(1)

    # Steam update
    steam_match = re.search(
        r"Last Steam Update\s+(.+?)(?:Game version|Last checked)",
        text,
        re.IGNORECASE
    )

    if steam_match:
        result["steam_update"] = clean(steam_match.group(1))

    # Descripción
    description = None

    for p in soup.find_all("p"):
        p_text = clean(p.get_text(" ", strip=True))

        if (
            p_text
            and len(p_text) > 80
            and "Steam" not in p_text
            and "Download" not in p_text
        ):
            description = p_text
            break

    result["description"] = description

    # SteamDB
    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "steamdb.info" in href:
            result["steamdb_url"] = href
            break

    # Géneros
    genres = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/genre/" in href:
            name = clean(a.get_text(" ", strip=True))

            if name:
                genres.add(name)

    result["genres"] = sorted(genres)

    return result


def main():
    print("Downloading AnkerGames catalog...")

    soup = get_soup(GAMES_URL)

    listing_games = extract_listing_game_data(soup)

    print(f"Games discovered on listing page: {len(listing_games)}")

    # Las fichas descubiertas actualmente.
    urls = sorted(listing_games.keys())

    games = []

    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}")

        try:
            game = parse_detail_page(url)

            # Usamos el título del listado si la ficha no lo proporciona.
            if not game["title"]:
                game["title"] = listing_games[url]["title"]

            games.append(game)

        except Exception as exc:
            print(f"ERROR: {url} -> {exc}")

        # Evitamos hacer peticiones demasiado agresivas.
        time.sleep(1)

    games.sort(
        key=lambda x: (x.get("title") or "").lower()
    )

    output = {
        "source": {
            "name": "AnkerGames",
            "url": BASE_URL,
            "catalog_url": GAMES_URL,
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        "total": len(games),
        "games": games
    }

    with open(
        "games.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(f"games.json created with {len(games)} games.")


if __name__ == "__main__":
    main()
