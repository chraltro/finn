"""Text-based scoring of listings for undervalued designer furniture signals."""

import re

# Keywords that suggest genuine mid-century Danish design
MATERIAL_KEYWORDS = {
    "teak": 5,
    "palisander": 8,
    "rosewood": 8,
    "massiv": 4,
    "heltre": 4,
    "eik": 2,
    "valnøtt": 3,
    "walnut": 3,
    "papircord": 5,
    "flet": 3,
    "lær": 2,  # leather
    "skinn": 2,
}

# Period keywords
PERIOD_KEYWORDS = {
    "dansk": 3,
    "dansk design": 6,
    "danish": 4,
    "danish design": 6,
    "mid-century": 5,
    "midcentury": 5,
    "60-tall": 4,
    "60-tallet": 4,
    "50-tall": 5,
    "50-tallet": 5,
    "70-tall": 2,
    "retro": 2,
    "vintage": 2,
}

# Estate/moving sale keywords (goldmine signals)
ESTATE_KEYWORDS = {
    "arv": 8,
    "dødsbo": 10,
    "bo-oppgjør": 8,
    "flytte": 6,
    "flyttesalg": 8,
    "plassmangel": 6,
    "må selges": 7,
    "ryddesalg": 7,
    "oppussing": 4,
    "garasjesalg": 5,
    "loppemarked": 3,
}

# Negative signals - reproductions and mass-market
REPRODUCTION_KEYWORDS = {
    "kopi": -15,
    "reproduksjon": -15,
    "inspirert av": -10,
    "inspirert": -5,
    "stil": -3,
    "replika": -15,
    "replica": -15,
    "ny produksjon": -8,
}

MASS_MARKET_KEYWORDS = {
    "ikea": -20,
    "jysk": -15,
    "bohus": -10,
    "skeidar": -10,
    "living": -5,
    "chilli": -8,
    "møbelringen": -8,
    "kid interiør": -8,
}


def score_keywords(listing):
    """Score a listing based on keyword analysis.

    Returns dict with:
        keyword_score: int total score
        matched_keywords: dict of category -> matched keywords
        signals: list of human-readable signal descriptions
    """
    text = f"{listing.title} {listing.description}".lower()

    total_score = 0
    matched = {
        "material": [],
        "period": [],
        "estate_sale": [],
        "reproduction": [],
        "mass_market": [],
    }
    signals = []

    # Material keywords
    for kw, score in MATERIAL_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
            total_score += score
            matched["material"].append(kw)

    if matched["material"]:
        signals.append(f"Materials: {', '.join(matched['material'])}")

    # Period keywords (check longer phrases first)
    sorted_period = sorted(PERIOD_KEYWORDS.items(), key=lambda x: -len(x[0]))
    seen_period = set()
    for kw, score in sorted_period:
        if kw in seen_period:
            continue
        if re.search(re.escape(kw), text, re.IGNORECASE):
            total_score += score
            matched["period"].append(kw)
            # Mark sub-phrases as seen to avoid double-counting
            for word in kw.split():
                seen_period.add(word)

    if matched["period"]:
        signals.append(f"Period signals: {', '.join(matched['period'])}")

    # Estate/moving sale keywords
    for kw, score in ESTATE_KEYWORDS.items():
        if re.search(re.escape(kw), text, re.IGNORECASE):
            total_score += score
            matched["estate_sale"].append(kw)

    if matched["estate_sale"]:
        signals.append(f"Estate/moving sale: {', '.join(matched['estate_sale'])}")

    # Reproduction keywords (negative)
    for kw, score in REPRODUCTION_KEYWORDS.items():
        if re.search(re.escape(kw), text, re.IGNORECASE):
            total_score += score
            matched["reproduction"].append(kw)

    if matched["reproduction"]:
        signals.append(f"WARNING - reproduction signals: {', '.join(matched['reproduction'])}")

    # Mass market keywords (negative)
    for kw, score in MASS_MARKET_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
            total_score += score
            matched["mass_market"].append(kw)

    if matched["mass_market"]:
        signals.append(f"WARNING - mass market brand: {', '.join(matched['mass_market'])}")

    return {
        "keyword_score": total_score,
        "matched_keywords": matched,
        "signals": signals,
    }
