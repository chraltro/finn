#!/usr/bin/env python3
"""Finn.no Danish Design Furniture Finder.

Searches Finn.no for undervalued Danish mid-century design furniture.
Scores listings based on designer/manufacturer recognition, keywords,
and price anomalies to find hidden gems.

Usage:
    python main.py                      # Run full search (all tiers)
    python main.py --tier1              # Named designer searches only
    python main.py --tier2              # Generic/vague searches only
    python main.py --query "teak stol"  # Single search term
    python main.py --playwright         # Use Playwright for JS rendering
    python main.py --min-score 20       # Only show listings scoring >= 20
    python main.py --max-pages 2        # Limit search pages per query
    python main.py --fetch-details      # Fetch full details for each listing
    python main.py --csv                # Also save CSV output
"""

import argparse
import logging
import sys

from alerts.notifier import print_alerts, save_csv, save_results
from scoring.designer_matcher import DesignerMatcher
from scoring.keyword_scorer import score_keywords
from scoring.price_scorer import PriceScorer
from scraper.config import SCORING_WEIGHTS, load_search_terms
from scraper.finn_search import FinnSearcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def compute_total_score(listing, designer_match, keyword_result, price_result):
    """Compute total score for a listing from all scoring components."""
    total = 0

    # Designer/manufacturer scoring
    designer_score = 0
    if designer_match["has_manufacturer_no_designer"]:
        designer_score += SCORING_WEIGHTS["manufacturer_match"]
    if designer_match["designers"]:
        if designer_match["designer_recognition"] == "low":
            designer_score += SCORING_WEIGHTS["designer_low_recognition"]
        elif designer_match["designer_recognition"] == "medium":
            designer_score += SCORING_WEIGHTS["designer_low_recognition"] // 2

    total += designer_score
    total += keyword_result["keyword_score"]
    total += price_result["price_score"]

    # Seller type
    if listing.is_dealer:
        total += SCORING_WEIGHTS["dealer_penalty"]
    else:
        total += SCORING_WEIGHTS["private_seller"]

    # Clamp to 0-100
    total = max(0, min(100, total))

    return total, designer_score


def run_search(searcher, queries, max_pages=3):
    """Run search for a list of query terms, deduplicating by finn_kode."""
    all_listings = {}

    for i, query in enumerate(queries):
        logger.info("Searching [%d/%d]: '%s'", i + 1, len(queries), query)
        try:
            results = searcher.search(query, max_pages=max_pages)
            new_count = 0
            for listing in results:
                if listing.finn_kode not in all_listings:
                    all_listings[listing.finn_kode] = listing
                    new_count += 1
            logger.info(
                "  Found %d results, %d new unique listings", len(results), new_count
            )
        except Exception as e:
            logger.error("  Error searching '%s': %s", query, e)

    return list(all_listings.values())


def score_listings(listings, fetch_details=False, searcher=None):
    """Score all listings using designer matching, keywords, and price analysis."""
    matcher = DesignerMatcher()
    price_scorer = PriceScorer()
    scored = []

    for i, listing in enumerate(listings):
        if fetch_details and searcher:
            logger.info(
                "Fetching details [%d/%d]: %s", i + 1, len(listings), listing.finn_kode
            )
            try:
                searcher.fetch_listing_details(listing)
            except Exception as e:
                logger.warning("Failed to fetch details for %s: %s", listing.finn_kode, e)

        # Only score active listings
        if not listing.is_active:
            continue

        designer_match = matcher.match(listing)
        keyword_result = score_keywords(listing)
        price_result = price_scorer.score(listing, designer_match)
        total_score, designer_score = compute_total_score(
            listing, designer_match, keyword_result, price_result
        )

        result = {
            "total_score": total_score,
            "designer_score": designer_score,
            "designer_match": designer_match,
            "keyword_result": keyword_result,
            "price_result": price_result,
        }

        scored.append((listing, result))

    return scored


def main():
    parser = argparse.ArgumentParser(
        description="Finn.no Danish Design Furniture Finder"
    )
    parser.add_argument(
        "--tier1", action="store_true", help="Only run Tier 1 (named designer) searches"
    )
    parser.add_argument(
        "--tier2", action="store_true", help="Only run Tier 2 (generic/vague) searches"
    )
    parser.add_argument("--query", type=str, help="Run a single search query")
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Use Playwright for JS-rendered pages",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=15,
        help="Minimum score to display in alerts (default: 15)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max search result pages per query (default: 3)",
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch full listing details (slower but more accurate scoring)",
    )
    parser.add_argument(
        "--csv", action="store_true", help="Also save results as CSV"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build query list
    if args.query:
        queries = [args.query]
    else:
        terms = load_search_terms()
        queries = []
        if args.tier1 or (not args.tier1 and not args.tier2):
            queries.extend(terms["tier1_named_designer"])
        if args.tier2 or (not args.tier1 and not args.tier2):
            queries.extend(terms["tier2_generic"])

    logger.info("Starting search with %d queries", len(queries))

    # Initialize searcher
    searcher = FinnSearcher(use_playwright=args.playwright)

    # Run searches
    listings = run_search(searcher, queries, max_pages=args.max_pages)
    logger.info("Total unique listings found: %d", len(listings))

    if not listings:
        print("\nNo listings found. Finn.no may be blocking requests.")
        print("Try running with --playwright flag for JS-rendered content.")
        print("You may need to install Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(0)

    # Score listings
    scored = score_listings(
        listings, fetch_details=args.fetch_details, searcher=searcher
    )

    # Output results
    print_alerts(scored, min_score=args.min_score)
    save_results(scored)
    if args.csv:
        save_csv(scored)

    # Summary stats
    high = sum(1 for _, r in scored if r["total_score"] >= 30)
    medium = sum(1 for _, r in scored if 15 <= r["total_score"] < 30)
    low = sum(1 for _, r in scored if r["total_score"] < 15)
    print(f"\nSummary: {len(scored)} listings scored")
    print(f"  High potential (30+): {high}")
    print(f"  Medium potential (15-29): {medium}")
    print(f"  Low potential (<15): {low}")


if __name__ == "__main__":
    main()
