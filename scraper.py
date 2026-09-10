import requests
from bs4 import BeautifulSoup


URL = "https://ankergames.net/game/persona-3-reload"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def main():

    print("Opening:", URL)

    response = requests.get(
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
    print("PAGE TITLE")
    print("=" * 60)

    if soup.title:
        print(
            soup.title.get_text(
                strip=True
            )
        )

    print()
    print("=" * 60)
    print("HEADINGS")
    print("=" * 60)

    for element in soup.find_all(
        ["h1", "h2", "h3"]
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        if text:
            print(
                element.name,
                ":",
                text
            )

    print()
    print("=" * 60)
    print("INTERESTING TEXT")
    print("=" * 60)

    keywords = [
        "version",
        "build",
        "size",
        "release",
        "upload",
        "download"
    ]

    seen = set()

    for element in soup.find_all(
        ["div", "span", "p", "li", "a"]
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        lower = text.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):

            text = text[:500]

            if text not in seen:

                seen.add(text)

                print(text)

    print()
    print("=" * 60)
    print("LINKS")
    print("=" * 60)

    for link in soup.find_all(
        "a",
        href=True
    ):

        text = link.get_text(
            " ",
            strip=True
        )

        href = link["href"]

        if text:

            print(
                text[:150],
                "=>",
                href
            )


if __name__ == "__main__":
    main()
