import requests
from bs4 import BeautifulSoup


URL = "https://ankergames.net/games-list"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def main():

    session = requests.Session()

    response = session.get(
        URL,
        headers=HEADERS,
        timeout=60
    )

    print("HTTP:", response.status_code)
    print("HTML:", len(response.text))

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    print()
    print("=" * 60)
    print("LIVEWIRE COMPONENTS")
    print("=" * 60)

    components = soup.find_all(
        attrs={"wire:id": True}
    )

    print(
        "Components:",
        len(components)
    )

    for i, component in enumerate(
        components
    ):

        print()
        print(
            f"COMPONENT {i}"
        )

        print(
            "wire:id:",
            component.get("wire:id")
        )

        print(
            "wire:snapshot:",
            bool(
                component.get(
                    "wire:snapshot"
                )
            )
        )

        print(
            "HTML tag:",
            component.name
        )

    print()
    print("=" * 60)
    print("LOAD MORE")
    print("=" * 60)

    # Buscar cualquier elemento que contenga
    # "Load More Games".
    for element in soup.find_all():

        text = element.get_text(
            " ",
            strip=True
        )

        if (
            "Load More Games"
            in text
        ):

            print()
            print(
                "TAG:",
                element.name
            )

            print(
                "TEXT:",
                text[:300]
            )

            print(
                "ATTRIBUTES:"
            )

            for key, value in (
                element.attrs.items()
            ):

                print(
                    f"  {key}: {value}"
                )

            print("-" * 40)

    print()
    print("=" * 60)
    print("WIRE:CLICK")
    print("=" * 60)

    clickable = soup.find_all(
        attrs={"wire:click": True}
    )

    print(
        "wire:click elements:",
        len(clickable)
    )

    for element in clickable:

        print()
        print(
            "TAG:",
            element.name
        )

        print(
            "wire:click:",
            element.get(
                "wire:click"
            )
        )

        print(
            "TEXT:",
            element.get_text(
                " ",
                strip=True
            )[:200]
        )

    print()
    print("=" * 60)
    print("GAME LINKS")
    print("=" * 60)

    game_links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/game/" in href:

            game_links.append(
                href
            )

    # Eliminar duplicados.
    game_links = list(
        dict.fromkeys(
            game_links
        )
    )

    print(
        "Game links:",
        len(game_links)
    )

    for link in game_links[:35]:

        print(
            link
        )


if __name__ == "__main__":
    main()
