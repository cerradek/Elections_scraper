import csv
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

def get_soup(url: str) -> BeautifulSoup:
    """Stáhne HTML stránku a vrátí BeautifulSoup objekt."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")

def validate_args(args: list[str]) -> tuple[str, str] | None:
    """Ověří počet argumentů a základní formát vstupní URL."""
    if len(args) != 3:
        print("Chyba: zadej 2 argumenty: URL a jméno výstupního CSV souboru.")
        return None

    url, filename = args[1], args[2]

    if "volby.cz" not in url or "ps32" not in url:
        print("Chyba: první argument musí být platný odkaz na územní celek z volby.cz.")
        return None

    if not filename.endswith(".csv"):
        print("Chyba: druhý argument musí být jméno souboru s příponou .csv.")
        return None
    return url, filename

def parse_municipality_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str, str]]:
    """Najde odkazy na detail obcí a vrátí kód, název a URL detailu."""
    municipalities = []
    rows = soup.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        link = row.find("a")
        if not link or "href" not in link.attrs:
            continue

        code = cells[0].get_text(strip=True)
        name = cells[1].get_text(strip=True)
        detail_url = urljoin(base_url, link["href"])

        if code.isdigit() and name:
            municipalities.append((code, name, detail_url))

    return municipalities

def parse_main_results(soup: BeautifulSoup) -> tuple[str, str, str]:
    """Vrátí voliči v seznamu, vydané obálky a platné hlasy."""
    tables = soup.find_all("table")
    first_table = tables[0]
    cells = first_table.find_all("td", class_="cislo")

    registered = cells[3].get_text(strip=True)
    envelopes = cells[4].get_text(strip=True)
    valid_votes = cells[7].get_text(strip=True)

    return registered, envelopes, valid_votes

def parse_party_results(soup: BeautifulSoup) -> dict[str, str]:
    """Vrátí slovník: název strany -> počet hlasů."""
    parties = {}
    tables = soup.find_all("table")

    for table in tables[1:]:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            party = cells[1].get_text(strip=True)
            votes = cells[2].get_text(strip=True)

            if party:
                parties[party] = votes

    return parties

def scrape_municipality(detail_url: str) -> tuple[str, str, str, dict[str, str]]:
    """Stáhne detail obce a vrátí hlavní statistiky a hlasy pro strany."""
    soup = get_soup(detail_url)
    registered, envelopes, valid_votes = parse_main_results(soup)
    parties = parse_party_results(soup)
    return registered, envelopes, valid_votes, parties

def collect_data(url: str) -> list[dict[str, str]]:
    """Projde všechny obce ve vybraném územním celku a vrátí data pro CSV."""
    soup = get_soup(url)
    municipalities = parse_municipality_links(soup, url)

    rows = []
    for code, name, detail_url in municipalities:
        registered, envelopes, valid_votes, parties = scrape_municipality(detail_url)
        row = {
            "code": code,
            "location": name,
            "registered": registered,
            "envelopes": envelopes,
            "valid": valid_votes,
        }
        row.update(parties)
        rows.append(row)

    return rows

def save_to_csv(filename: str, data: list[dict[str, str]]) -> None:
    """Uloží získaná data do CSV souboru."""
    if not data:
        print("Chyba: nepodařilo se získat žádná data.")
        return

    headers = []
    for row in data:
        for key in row:
            if key not in headers:
                headers.append(key)

    with open(filename, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def main() -> None:
    """Hlavní funkce programu."""
    validated = validate_args(sys.argv)
    if validated is None:
        sys.exit(1)

    url, filename = validated
    data = collect_data(url)
    save_to_csv(filename, data)
    print(f"Hotovo. Data byla uložena do souboru: {filename}")

if __name__ == "__main__":
    main()