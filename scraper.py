import requests
from bs4 import BeautifulSoup

URL = "https://ankergames.net/games-list"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("HTTP:", response.status_code)
print("HTML:", len(response.text))

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

print()
print("BUTTONS:")

buttons = soup.find_all("button")

print(
    "Number of buttons:",
    len(buttons)
)

for i, button in enumerate(buttons):

    text = button.get_text(
        " ",
        strip=True
    )

    print(
        f"BUTTON {i}: {text!r}"
    )

print()
print("LOAD MORE SEARCH:")

text = soup.get_text(
    " ",
    strip=True
)

position = text.lower().find(
    "load more"
)

if position >= 0:

    print(
        text[
            max(0, position - 500):
            position + 1000
        ]
    )

else:

    print(
        "Load More not found"
    )

print()
print("LIVEWIRE ELEMENTS:")

for element in soup.find_all(
    attrs={"wire:click": True}
):

    print(
        "wire:click =",
        element.get("wire:click")
    )

    print(
        "text =",
        element.get_text(
            " ",
            strip=True
        )[:200]
    )

print()
print("DONE")
