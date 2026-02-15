"""Configuration for Finn.no scraper."""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# Finn.no URL patterns
FINN_SEARCH_URL = "https://www.finn.no/recommerce/forsale/search"
FINN_ITEM_URL = "https://www.finn.no/recommerce/forsale/item/{finn_kode}"

# Category filters for furniture
CATEGORY_FILTERS = {
    "mobler_og_interior": "0.78",
    "sofaer_og_lenestoler": "1.78.7756",
    "lenestoler": "2.78.7756.210",
}

# Request settings
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.5
REQUEST_TIMEOUT = 30

# Headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,nn;q=0.7,en-US;q=0.6,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Geographic priority (postal code ranges for target areas)
PRIORITY_REGIONS = {
    "Vestfold": {"postal_prefixes": ["30", "31", "32", "33"]},
    "Oslo": {"postal_prefixes": ["0"]},
    "Akershus": {"postal_prefixes": ["01", "02", "03", "13", "14", "20", "21"]},
    "Buskerud": {"postal_prefixes": ["30", "33", "34", "35", "36"]},
    "Østfold": {"postal_prefixes": ["15", "16", "17", "18", "19"]},
    "Telemark": {"postal_prefixes": ["37", "38", "39"]},
}

# Scoring weights
SCORING_WEIGHTS = {
    "manufacturer_match": 25,
    "designer_low_recognition": 20,
    "material_keywords": 10,
    "estate_sale_keywords": 15,
    "low_price_signal": 20,
    "private_seller": 5,
    "small_town": 5,
    "multiple_items_seller": 5,
    "dealer_penalty": -20,
    "market_aware_price_penalty": -15,
    "reproduction_penalty": -30,
    "mass_market_penalty": -25,
}


def load_json(filename):
    """Load a JSON file from the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_search_terms():
    """Load search terms from JSON."""
    return load_json("search_terms.json")


def load_designers():
    """Load designer/manufacturer database."""
    return load_json("designers.json")


def load_price_reference():
    """Load price reference data."""
    return load_json("price_reference.json")
