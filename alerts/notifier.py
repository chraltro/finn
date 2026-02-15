"""Alert system for high-scoring listings.

Supports console output and optional file-based reports.
Email/Slack/Telegram can be added later.
"""

import json
import logging
import os
from datetime import datetime

from scraper.config import RESULTS_DIR

logger = logging.getLogger(__name__)


def format_listing_alert(listing, score_result):
    """Format a single listing as a human-readable alert."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  SCORE: {score_result['total_score']}/100")
    lines.append(f"  {listing.title}")
    lines.append(f"  Price: {listing.price_text or listing.price or 'N/A'} NOK")
    lines.append(f"  Location: {listing.location or 'Unknown'}")
    lines.append(f"  URL: {listing.url}")
    lines.append(f"  FINN-kode: {listing.finn_kode}")
    lines.append("")

    if score_result.get("designer_match", {}).get("designers"):
        lines.append(
            f"  Designers: {', '.join(score_result['designer_match']['designers'])}"
        )
    if score_result.get("designer_match", {}).get("manufacturers"):
        lines.append(
            f"  Manufacturers: {', '.join(score_result['designer_match']['manufacturers'])}"
        )
    if score_result.get("designer_match", {}).get("has_manufacturer_no_designer"):
        lines.append("  *** MANUFACTURER FOUND, NO DESIGNER NAME - possible hidden gem ***")

    if score_result.get("price_result", {}).get("potential_value"):
        lines.append(f"  Value: {score_result['price_result']['potential_value']}")

    all_signals = []
    for key in ["keyword_result", "price_result", "designer_match"]:
        result = score_result.get(key, {})
        if result.get("signals"):
            all_signals.extend(result["signals"])

    if all_signals:
        lines.append("  Signals:")
        for signal in all_signals:
            lines.append(f"    - {signal}")

    if listing.description:
        desc_preview = listing.description[:200]
        if len(listing.description) > 200:
            desc_preview += "..."
        lines.append(f"  Description: {desc_preview}")

    lines.append("=" * 70)
    return "\n".join(lines)


def print_alerts(scored_listings, min_score=15):
    """Print alerts for high-scoring listings to console."""
    high_scorers = [
        (listing, result)
        for listing, result in scored_listings
        if result["total_score"] >= min_score
    ]

    if not high_scorers:
        print("\nNo high-scoring listings found in this run.")
        return

    high_scorers.sort(key=lambda x: -x[1]["total_score"])

    print(f"\n{'#' * 70}")
    print(f"  FINN DESIGN FINDER - {len(high_scorers)} potential finds")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#' * 70}\n")

    for listing, result in high_scorers:
        print(format_listing_alert(listing, result))
        print()


def save_results(scored_listings, filename=None):
    """Save all results to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.json"

    os.makedirs(RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(RESULTS_DIR, filename)

    output = {
        "timestamp": datetime.now().isoformat(),
        "total_listings": len(scored_listings),
        "listings": [],
    }

    for listing, result in scored_listings:
        entry = listing.to_dict()
        entry["scoring"] = {
            "total_score": result["total_score"],
            "keyword_score": result.get("keyword_result", {}).get("keyword_score", 0),
            "price_score": result.get("price_result", {}).get("price_score", 0),
            "designer_score": result.get("designer_score", 0),
            "price_ratio": result.get("price_result", {}).get("price_ratio"),
            "potential_value": result.get("price_result", {}).get("potential_value", ""),
            "matched_designers": result.get("designer_match", {}).get("designers", []),
            "matched_manufacturers": result.get("designer_match", {}).get(
                "manufacturers", []
            ),
            "has_manufacturer_no_designer": result.get("designer_match", {}).get(
                "has_manufacturer_no_designer", False
            ),
        }
        # Collect all signals
        signals = []
        for key in ["keyword_result", "price_result"]:
            r = result.get(key, {})
            signals.extend(r.get("signals", []))
        entry["scoring"]["signals"] = signals
        output["listings"].append(entry)

    # Sort by score
    output["listings"].sort(key=lambda x: -x["scoring"]["total_score"])

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Results saved to %s", filepath)
    print(f"\nResults saved to: {filepath}")
    return filepath


def save_csv(scored_listings, filename=None):
    """Save results as CSV for easy spreadsheet review."""
    import csv

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.csv"

    os.makedirs(RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Score",
            "Title",
            "Price (NOK)",
            "Location",
            "URL",
            "FINN-kode",
            "Designers",
            "Manufacturers",
            "Potential Value",
            "Signals",
            "Search Query",
        ])

        sorted_listings = sorted(scored_listings, key=lambda x: -x[1]["total_score"])
        for listing, result in sorted_listings:
            designers = ", ".join(result.get("designer_match", {}).get("designers", []))
            manufacturers = ", ".join(
                result.get("designer_match", {}).get("manufacturers", [])
            )
            signals = []
            for key in ["keyword_result", "price_result"]:
                r = result.get(key, {})
                signals.extend(r.get("signals", []))

            writer.writerow([
                result["total_score"],
                listing.title,
                listing.price or "",
                listing.location,
                listing.url,
                listing.finn_kode,
                designers,
                manufacturers,
                result.get("price_result", {}).get("potential_value", ""),
                "; ".join(signals),
                listing.search_query,
            ])

    logger.info("CSV saved to %s", filepath)
    print(f"CSV saved to: {filepath}")
    return filepath
