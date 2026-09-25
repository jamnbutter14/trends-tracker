"""
Fetches Google Trends "interest over time" data for a fixed set of topics
and appends/merges it into trends_data.csv (one row per date).

Runs against Google's public (unofficial) JSON endpoints that back the
Explore page charts. These do NOT require signing in.
"""

import requests
import json
import time
import csv
import os
from datetime import datetime, timezone

# ---- CONFIGURE HERE ----------------------------------------------------
# These are the Knowledge Graph topic IDs taken straight from your Explore
# URL (the "/g/..." values after q=). Order here = column order in the CSV.
KEYWORDS = [
    "/g/11yjly_225",   # James
    "/g/11xt4k_q7r",   # Martin
    "/g/11xt4srq2w",   # Juhoon
    "/g/11xvlz7chy",   # Seonghyeon
    "/g/11xt00ktl_",   # Keonho
]

GEO = ""              # "" = Worldwide
TIMEFRAME = "today 1-m"   # a ~month window is what makes Google return DAILY
                           # points instead of hourly ones. We keep merging
                           # this rolling window into the CSV below.
OUTPUT_FILE = "trends_data.csv"
# -------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_timeline():
    session = requests.Session()
    # Visiting the homepage first sets cookies Google expects on later calls.
    session.get("https://trends.google.com/", headers=HEADERS, timeout=30)
    time.sleep(1)

    explore_req = {
        "comparisonItem": [
            {"keyword": kw, "geo": GEO, "time": TIMEFRAME} for kw in KEYWORDS
        ],
        "category": 0,
        "property": "",
    }
    r = session.get(
        "https://trends.google.com/trends/api/explore",
        params={"hl": "en-US", "tz": "0", "req": json.dumps(explore_req)},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    # Google prefixes the JSON with ")]}',\n" — strip it before parsing.
    data = json.loads(r.text[5:])

    widget = next(w for w in data["widgets"] if w["id"] == "TIMESERIES")
    time.sleep(1)

    r2 = session.get(
        "https://trends.google.com/trends/api/widgetdata/multiline",
        params={
            "hl": "en-US",
            "tz": "0",
            "req": json.dumps(widget["request"]),
            "token": widget["token"],
        },
        headers=HEADERS,
        timeout=30,
    )
    r2.raise_for_status()
    data2 = json.loads(r2.text[5:])
    return data2["default"]["timelineData"]


def load_existing_rows():
    rows = {}
    if os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    rows[row[0]] = row[1:]
    return rows


def main():
    timeline = fetch_timeline()

    rows = load_existing_rows()
    for point in timeline:
        date_str = datetime.fromtimestamp(
            int(point["time"]), tz=timezone.utc
        ).strftime("%Y-%m-%d")
        rows[date_str] = [str(v) for v in point["value"]]

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date"] + KEYWORDS)
        for date_str in sorted(rows):
            writer.writerow([date_str] + rows[date_str])

    print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
