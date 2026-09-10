from playwright.sync_api import sync_playwright

URL = "https://ankergames.net/games-list"

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page()

    print("Opening page...")

    page.goto(
        URL,
        wait_until="networkidle",
        timeout=120000
    )

    print("Page loaded.")

    print()
    print("PAGE TITLE:")
    print(page.title())

    print()
    print("BUTTONS:")

    buttons = page.locator("button")

    print(
        "Number of buttons:",
        buttons.count()
    )

    for i in range(
        min(buttons.count(), 100)
    ):

        try:

            text = buttons.nth(i).inner_text(
                timeout=2000
            )

            print(
                f"BUTTON {i}: {text!r}"
            )

        except:
            pass

    print()
    print("LINKS CONTAINING GAME:")

    links = page.locator("a")

    found = 0

    for i in range(
        min(links.count(), 500)
    ):

        try:

            href = links.nth(i).get_attribute(
                "href"
            )

            if href and "/game/" in href:

                text = links.nth(i).inner_text(
                    timeout=1000
                )

                print(
                    f"{href} -> {text[:100]!r}"
                )

                found += 1

        except:
            pass

    print()
    print(
        "GAME LINKS FOUND:",
        found
    )

    print()
    print("TEXT AROUND LOAD MORE:")

    body_text = page.locator(
        "body"
    ).inner_text()

    position = body_text.lower().find(
        "load more"
    )

    if position >= 0:

        print(
            body_text[
                max(0, position - 300):
                position + 500
            ]
        )

    else:

        print(
            "Load More text not found."
        )

    browser.close()
