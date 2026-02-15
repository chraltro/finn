"""Match listings to known designers and manufacturers."""

import logging
import re

from scraper.config import load_designers

logger = logging.getLogger(__name__)


class DesignerMatcher:
    """Matches listing text against known designers and manufacturers."""

    def __init__(self):
        data = load_designers()
        self.manufacturers = data["manufacturers"]
        self.designers = data["designers"]
        self._build_patterns()

    def _build_patterns(self):
        """Pre-compile regex patterns for all names and aliases."""
        self._manufacturer_patterns = {}
        for name, info in self.manufacturers.items():
            all_names = [name] + info.get("aliases", [])
            patterns = [re.compile(re.escape(n), re.IGNORECASE) for n in all_names]
            self._manufacturer_patterns[name] = patterns

        self._designer_patterns = {}
        for name, info in self.designers.items():
            all_names = [name] + info.get("aliases", [])
            patterns = [re.compile(re.escape(n), re.IGNORECASE) for n in all_names]
            self._designer_patterns[name] = patterns

        # Known model numbers (often found stamped on furniture)
        self._model_patterns = {
            "CH24": ("Hans J. Wegner", "Y-stol"),
            "CH23": ("Hans J. Wegner", "CH23"),
            "CH07": ("Hans J. Wegner", "Shell Chair"),
            "FD134": ("Peter Hvidt", "Boomerang chair"),
            "FD 134": ("Peter Hvidt", "Boomerang chair"),
            "FD133": ("Finn Juhl", "Spade chair"),
            "FD 133": ("Finn Juhl", "Spade chair"),
        }
        self._model_re = {
            model: re.compile(re.escape(model), re.IGNORECASE)
            for model in self._model_patterns
        }

    def match(self, listing):
        """Analyze a listing and return match results.

        Returns dict with:
            manufacturers: list of matched manufacturer names
            designers: list of matched designer names
            designer_recognition: 'high', 'medium', 'low', or None
            model_matches: list of (model, designer, piece) tuples
            has_manufacturer_no_designer: bool (key signal for undervalued)
        """
        text = f"{listing.title} {listing.description}".strip()
        if not text:
            return self._empty_result()

        result = {
            "manufacturers": [],
            "designers": [],
            "designer_recognition": None,
            "model_matches": [],
            "has_manufacturer_no_designer": False,
        }

        # Check manufacturers
        for name, patterns in self._manufacturer_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    result["manufacturers"].append(name)
                    break

        # Check designers
        for name, patterns in self._designer_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    result["designers"].append(name)
                    recognition = self.designers[name].get("recognition_level", "low")
                    if result["designer_recognition"] is None or _recognition_priority(
                        recognition
                    ) < _recognition_priority(result["designer_recognition"]):
                        result["designer_recognition"] = recognition
                    break

        # Check model numbers
        for model, (designer, piece) in self._model_patterns.items():
            if self._model_re[model].search(text):
                result["model_matches"].append((model, designer, piece))
                # Add designer if not already found
                if designer not in result["designers"]:
                    result["designers"].append(designer)
                    recognition = self.designers.get(designer, {}).get(
                        "recognition_level", "low"
                    )
                    if result["designer_recognition"] is None or _recognition_priority(
                        recognition
                    ) < _recognition_priority(result["designer_recognition"]):
                        result["designer_recognition"] = recognition

        # Key signal: manufacturer mentioned but no designer
        if result["manufacturers"] and not result["designers"]:
            result["has_manufacturer_no_designer"] = True

        return result

    def _empty_result(self):
        return {
            "manufacturers": [],
            "designers": [],
            "designer_recognition": None,
            "model_matches": [],
            "has_manufacturer_no_designer": False,
        }

    def get_possible_designers_for_manufacturer(self, manufacturer_name):
        """Given a manufacturer, return possible designers."""
        info = self.manufacturers.get(manufacturer_name, {})
        return info.get("notable_designers", [])


def _recognition_priority(level):
    """Lower number = higher priority (we want to keep the lowest recognition)."""
    return {"low": 0, "medium": 1, "high": 2}.get(level, 1)
