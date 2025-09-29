import json
import sqlite3

# Connect to SQLite
conn = sqlite3.connect("angi.db")
cursor = conn.cursor()

# =============================
# Ensure tables exist (with UNIQUE constraints)
# =============================
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_code TEXT UNIQUE NOT NULL,
    state_name TEXT NOT NULL
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER NOT NULL,
    city_slug TEXT NOT NULL,
    FOREIGN KEY (state_id) REFERENCES states(id),
    UNIQUE (state_id, city_slug)
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niche_code TEXT UNIQUE NOT NULL,
    niche_name TEXT NOT NULL
)
"""
)

conn.commit()

# =============================
# Load states & cities
# =============================
with open("angi_states_and_cities.json", "r", encoding="utf-8") as f:
    states_data = json.load(f)

for state in states_data:
    state_code = state["state_code"]
    state_name = state["state_name"]

    cursor.execute(
        "INSERT OR IGNORE INTO states (state_code, state_name) VALUES (?, ?)",
        (state_code, state_name),
    )
    conn.commit()

    # Get state_id
    cursor.execute("SELECT id FROM states WHERE state_code=?", (state_code,))
    state_id = cursor.fetchone()[0]

    # Insert cities (no duplicates thanks to UNIQUE constraint)
    for city in state["cities"]:
        cursor.execute(
            "INSERT OR IGNORE INTO cities (state_id, city_slug) VALUES (?, ?)",
            (state_id, city),
        )
    conn.commit()

print("✅ States and cities loaded")

# =============================
# Load niches
# =============================
with open("angi_niches.json", "r", encoding="utf-8") as f:
    niches_data = json.load(f)

for niche in niches_data:
    niche_code = niche["niche_code"]
    niche_name = niche["niche_name"]

    cursor.execute(
        "INSERT OR IGNORE INTO niches (niche_code, niche_name) VALUES (?, ?)",
        (niche_code, niche_name),
    )
conn.commit()

print("✅ Niches loaded")

# Close connection
conn.close()
print("🎉 All data loaded into angi.db")
