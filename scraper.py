import sqlite3
import re
import csv
from botasaurus.soupify import soupify
from botasaurus_requests import async_request, imap_enum


# ==============================
# Database Access
# ==============================


def get_states():
    conn = sqlite3.connect("angi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, state_code, state_name FROM states ORDER BY state_name")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_cities(state_id):
    conn = sqlite3.connect("angi.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, city_slug FROM cities WHERE state_id=? ORDER BY city_slug",
        (state_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_niches():
    conn = sqlite3.connect("angi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, niche_code, niche_name FROM niches ORDER BY niche_name")
    rows = cursor.fetchall()
    conn.close()
    return rows


def generate_url(state_code, city_slug, niche_code):
    return (
        f"https://www.angi.com/companylist/us/{state_code}/{city_slug}/{niche_code}.htm"
    )


# ==============================
# Profile Parsing
# ==============================


def parse_profile(response, url):
    """Parse phone, website, and email from a profile page"""
    try:
        soup = soupify(response.text)
        scripts = soup.find_all("script")
        phone, website, email = "N/A", "N/A", "N/A"

        for script in scripts:
            if not script.string:
                continue
            text = script.string

            # --- Phone ---
            if "+1" in text:
                phone_match = re.search(
                    r'\\"phoneNumber\\"\s*:\s*\\"(\+1[0-9\-]+)\\"', text
                )
                if phone_match:
                    phone = phone_match.group(1)

            # --- Email ---
            email_match = re.search(r'Additional email\s*-\s*([^\\"]+)', text)
            if email_match:
                candidate = email_match.group(1).strip()
                if re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+", candidate):
                    email = candidate.rstrip(".")

        # --- Website from HTML ---
        contact_div = soup.select_one("div.business-info a[role='link']")
        if contact_div and contact_div.get("href"):
            candidate = contact_div["href"]
            if "angi.com" not in candidate:
                website = candidate

        return {"phone": phone, "website": website, "email": email}

    except Exception as e:
        print(f"🔥 Error parsing profile {url}: {e}")
        return {"phone": "N/A", "website": "N/A", "email": "N/A"}


# ==============================
# City Scraping (with pagination)
# ==============================


def scrape_city(url):
    results = []
    page = 1
    max_page = 1

    while True:
        paged_url = f"{url}?page={page}" if page > 1 else url
        print(f"\n📄 Scraping page {page}: {paged_url}")

        # City listing request
        response = list(imap_enum([async_request("GET", paged_url)], size=1))[0][1]
        soup = soupify(response.text)

        # --- Extract pagination info ---
        footer = soup.select_one("div.PaginationFooter_root__HoNjH")
        if footer:
            current_tag = footer.select_one(
                "button.PaginationFooter_highlighted__tSL7o"
            )
            current_page = (
                int(current_tag.get_text(strip=True)) if current_tag else page
            )
            last_tag = footer.select_one("button[data-testid='last-page']")
            max_page = int(last_tag.get_text(strip=True)) if last_tag else current_page
            print(f"🔎 Pagination: current={current_page}, max={max_page}")

        # --- Business cards ---
        cards = soup.select("article.ProList_businessProCard__qvaeT")
        if not cards:
            print("⚠️ No business cards found, stopping.")
            break

        companies = []
        profile_requests = []

        for card in cards:
            name_tag = card.select_one("h4")
            name = name_tag.get_text(strip=True) if name_tag else "N/A"

            link_tag = card.select_one("a[data-testid='profile-link']")
            profile_url = link_tag["href"] if link_tag else "N/A"

            rating_tag = card.select_one(".RatingsLockup_ratingNumber__2CoLI")
            rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"

            reviews_tag = card.select_one(".RatingsLockup_reviewCount__u0DTP div")
            reviews = reviews_tag.get_text(strip=True) if reviews_tag else "N/A"

            company = {
                "name": name,
                "profile_url": "https://www.angi.com" + profile_url,
                "rating": rating,
                "reviews": reviews,
                "phone": "N/A",
                "website": "N/A",
                "email": "N/A",
            }
            companies.append(company)

            if profile_url != "N/A":
                full_url = (
                    "https://www.angi.com" + profile_url
                    if profile_url.startswith("/")
                    else profile_url
                )
                profile_requests.append((company, async_request("GET", full_url)))

        # --- Fetch all profiles in parallel and keep them matched ---
        requests = [req for _, req in profile_requests]
        for idx, response in imap_enum(requests, size=8):
            company, _ = profile_requests[idx]
            if response and not isinstance(response, Exception) and response.ok:
                pdata = parse_profile(response, response.url)
                company.update(pdata)
            else:
                print(f"⚠️ Failed profile request for {company['name']}")

        results.extend(companies)

        # --- Stop if last page reached ---
        if page >= max_page:
            print("✅ All pages scraped.")
            break

        page += 1

    return results


# ==============================
# User Interaction
# ==============================


def choose_multiple(options, prompt):
    for idx, item in enumerate(options, 1):
        print(f"{idx}. {item}")
    raw = input(f"{prompt} (comma-separated indices): ").strip()
    choices = []
    for val in raw.split(","):
        try:
            idx = int(val.strip())
            if 1 <= idx <= len(options):
                choices.append(idx - 1)
            else:
                print(f"❌ {val.strip()} is out of range, skipping.")
        except ValueError:
            print(f"❌ {val.strip()} is not a number, skipping.")
    return choices


def main():
    states = get_states()
    state_options = [f"{name} ({code.upper()})" for (_, code, name) in states]

    print("\n🌎 Select a state:")
    state_idx = choose_multiple(state_options, "Enter state number (only one)")
    if not state_idx:
        print("❌ No valid state selected, exiting.")
        return
    state_id, state_code, state_name = states[state_idx[0]]

    cities = get_cities(state_id)
    city_options = [slug for (_, slug) in cities]

    print(f"\n🏙️ Select one or more cities in {state_name}:")
    city_indices = choose_multiple(city_options, "Enter city numbers")
    if not city_indices:
        print("❌ No valid cities selected, exiting.")
        return

    niches = get_niches()
    niche_options = [
        f"{niche_name} ({niche_code})" for (_, niche_code, niche_name) in niches
    ]

    print("\n🛠️ Select a niche (service):")
    niche_idx = choose_multiple(niche_options, "Enter niche number (only one)")
    if not niche_idx:
        print("❌ No valid niche selected, exiting.")
        return
    _, niche_code, niche_name = niches[niche_idx[0]]

    all_companies = []

    for city_idx in city_indices:
        _, city_slug = cities[city_idx]
        url = generate_url(state_code, city_slug, niche_code)
        print(f"\n🔗 Generated URL for {city_slug}:\n{url}")

        print("\n🔍 Scraping companies...")
        companies = scrape_city(url)

        # Filter out companies with no phone
        companies = [c for c in companies if c["phone"] != "N/A"]

        all_companies.extend(companies)

    # === Save to CSV ===
    if all_companies:
        filename = f"angi_results_{state_code}_{niche_code}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_companies[0].keys())
            writer.writeheader()
            writer.writerows(all_companies)
        print(f"\n💾 Saved {len(all_companies)} companies to {filename}")
    else:
        print("⚠️ No companies found.")


if __name__ == "__main__":
    main()
