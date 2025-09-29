import re
import json
from botasaurus.request import request, Request
from botasaurus.soupify import soupify


@request(output=None)
def gather_niches(request: Request, data=None):
    """Scrape Angi nearme niches (categories)"""
    url = "https://www.angi.com/nearme/"
    response = request.get(url)
    soup = soupify(response)

    niches = []
    for link in soup.select("ul.Links_root__g9Yuz li a"):
        href = link.get("href", "")
        text = link.get("title") or link.text.strip()

        # Regex to capture slug from /nearme/{slug}/
        match = re.search(r"/nearme/([^/]+)/", href)
        if match:
            niche_code = match.group(1)
            niches.append({"niche_code": niche_code, "niche_name": text})

    # Save results to JSON
    with open("angi_niches.json", "w", encoding="utf-8") as f:
        json.dump(niches, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(niches)} niches to angi_niches.json")
    return niches


if __name__ == "__main__":
    gather_niches()
