import re
import json
from botasaurus.request import request, Request
from botasaurus.soupify import soupify


@request(output=None)
def gather_states(request: Request, data):
    """Scrape all state codes + names from Angi nearme page"""
    url = "https://www.angi.com/nearme/wood-floor-installers/"
    response = request.get(url)
    soup = soupify(response)

    states = []
    for link in soup.select("ul.Links_root__g9Yuz li a"):
        href = link.get("href", "")
        full_text = link.text.strip()
        # Extract the state name before "Wood floor installation pros"
        state_name = full_text.replace("Wood floor installation pros", "").strip()
        match = re.search(r"/us/([a-z]{2})/", href)
        if match:
            states.append({"state_code": match.group(1), "state_name": state_name})
    return states


@request(output=None, parallel=5)
def gather_cities(request: Request, state: dict):
    """Scrape all city slugs for a given state"""
    code = state["state_code"]
    url = f"https://www.angi.com/companylist/us/{code}/contractor.htm"
    response = request.get(url)
    soup = soupify(response)

    cities = []
    for link in soup.select("ul.Links_root__g9Yuz li a"):
        href = link.get("href", "")
        match = re.search(r"/us/[a-z]{2}/([^/]+)/contractor\.htm", href)
        if match:
            cities.append(match.group(1))

    state["cities"] = sorted(set(cities))
    return state


def scrape_all_states_and_cities():
    # Step 1: get states
    states = gather_states()

    # Step 2: gather cities in parallel
    results = gather_cities(states)

    # Step 3: save to JSON
    with open("angi_states_and_cities.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("✅ Saved results to angi_states_and_cities.json")
    return results


if __name__ == "__main__":
    scrape_all_states_and_cities()
