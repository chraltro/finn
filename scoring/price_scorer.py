"""Price anomaly detection for Finn.no listings.

Compares listing prices against known dealer/auction prices
to identify potentially undervalued pieces.
"""

import logging
import re

from scraper.config import load_price_reference

logger = logging.getLogger(__name__)


class PriceScorer:
    """Score listings based on price relative to known market values."""

    def __init__(self):
        data = load_price_reference()
        self.prices = data["prices"]
        self._build_patterns()

    def _build_patterns(self):
        """Pre-compile keyword patterns for each reference piece."""
        self._piece_patterns = []
        for piece in self.prices:
            patterns = []
            for kw in piece["keywords"]:
                patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
            self._piece_patterns.append((piece, patterns))

    def score(self, listing, designer_match=None):
        """Score a listing's price against reference values.

        Returns dict with:
            price_score: int (higher = more undervalued)
            matched_pieces: list of matched reference pieces
            price_ratio: float or None (listing price / dealer low price)
            potential_value: str description of potential value
            signals: list of human-readable signals
        """
        result = {
            "price_score": 0,
            "matched_pieces": [],
            "price_ratio": None,
            "potential_value": "",
            "signals": [],
        }

        if listing.price is None or listing.price <= 0:
            return result

        text = f"{listing.title} {listing.description}".lower()

        # Find matching reference pieces
        best_match = None
        best_ratio = None

        for piece, patterns in self._piece_patterns:
            match_count = sum(1 for p in patterns if p.search(text))
            if match_count == 0:
                continue

            result["matched_pieces"].append({
                "piece": piece["piece"],
                "designer": piece["designer"],
                "dealer_low": piece["dealer_price_low"],
                "dealer_high": piece["dealer_price_high"],
                "keyword_matches": match_count,
            })

            ratio = listing.price / piece["dealer_price_low"]

            if best_ratio is None or ratio < best_ratio:
                best_ratio = ratio
                best_match = piece

        # Also check designer match results for potential piece identification
        if designer_match and designer_match.get("designers"):
            for piece, patterns in self._piece_patterns:
                if piece["designer"] in designer_match["designers"]:
                    # Check if we already matched this piece
                    already_matched = any(
                        m["piece"] == piece["piece"] for m in result["matched_pieces"]
                    )
                    if not already_matched:
                        ratio = listing.price / piece["dealer_price_low"]
                        if best_ratio is None or ratio < best_ratio:
                            best_ratio = ratio
                            best_match = piece
                        result["matched_pieces"].append({
                            "piece": piece["piece"],
                            "designer": piece["designer"],
                            "dealer_low": piece["dealer_price_low"],
                            "dealer_high": piece["dealer_price_high"],
                            "keyword_matches": 0,
                            "matched_via": "designer",
                        })

        if best_match and best_ratio is not None:
            result["price_ratio"] = round(best_ratio, 2)

            if best_ratio <= 0.15:
                result["price_score"] = 30
                result["potential_value"] = (
                    f"AMAZING DEAL - {int(best_ratio * 100)}% of dealer low "
                    f"({best_match['dealer_price_low']}-{best_match['dealer_price_high']} NOK)"
                )
            elif best_ratio <= 0.25:
                result["price_score"] = 25
                result["potential_value"] = (
                    f"Great deal - {int(best_ratio * 100)}% of dealer low "
                    f"({best_match['dealer_price_low']}-{best_match['dealer_price_high']} NOK)"
                )
            elif best_ratio <= 0.40:
                result["price_score"] = 15
                result["potential_value"] = (
                    f"Good deal - {int(best_ratio * 100)}% of dealer low "
                    f"({best_match['dealer_price_low']}-{best_match['dealer_price_high']} NOK)"
                )
            elif best_ratio <= 0.60:
                result["price_score"] = 5
                result["potential_value"] = (
                    f"Fair price - {int(best_ratio * 100)}% of dealer low "
                    f"({best_match['dealer_price_low']}-{best_match['dealer_price_high']} NOK)"
                )
            else:
                result["price_score"] = -5
                result["potential_value"] = (
                    f"Market-aware price - {int(best_ratio * 100)}% of dealer low"
                )

            result["signals"].append(
                f"Price {listing.price} NOK vs dealer "
                f"{best_match['dealer_price_low']}-{best_match['dealer_price_high']} NOK "
                f"for {best_match['piece']}"
            )

        # General price signals (even without specific piece match)
        if listing.price <= 500:
            result["price_score"] += 5
            result["signals"].append("Very low price (under 500 NOK)")
        elif listing.price <= 1500:
            result["price_score"] += 3
            result["signals"].append("Low price range (under 1500 NOK)")

        return result
