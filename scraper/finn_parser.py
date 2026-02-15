"""HTML parsing for individual Finn.no listing pages."""

import json
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FinnListingParser:
    """Parse a Finn.no item page to extract listing details."""

    def __init__(self, html):
        self.soup = BeautifulSoup(html, "html.parser")
        self._json_data = self._extract_json_ld()
        self._next_data = self._extract_next_data()

    def _extract_json_ld(self):
        """Extract JSON-LD structured data if present."""
        script = self.soup.find("script", {"type": "application/ld+json"})
        if script and script.string:
            try:
                return json.loads(script.string)
            except json.JSONDecodeError:
                pass
        return {}

    def _extract_next_data(self):
        """Extract __NEXT_DATA__ if present."""
        script = self.soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            try:
                return json.loads(script.string)
            except json.JSONDecodeError:
                pass
        return {}

    def update_listing(self, listing):
        """Update a FinnListing with detailed info from the page."""
        # Try structured data first, then HTML fallbacks
        listing.title = self._get_title() or listing.title
        listing.description = self._get_description() or listing.description
        listing.location = self._get_location() or listing.location
        listing.date_posted = self._get_date_posted() or listing.date_posted
        listing.seller_name = self._get_seller_name() or listing.seller_name
        listing.is_dealer = self._check_is_dealer()
        listing.is_active = self._check_is_active()

        price = self._get_price()
        if price is not None:
            listing.price = price

        images = self._get_images()
        if images:
            listing.image_urls = images

        return listing

    def _get_title(self):
        """Extract listing title."""
        # JSON-LD
        if self._json_data.get("name"):
            return self._json_data["name"]

        # Next.js data
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                return ad.get("heading", ad.get("title", ""))
            except (KeyError, TypeError):
                pass

        # HTML fallbacks
        h1 = self.soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return ""

    def _get_description(self):
        """Extract listing description text."""
        # Next.js data
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                desc = ad.get("body", ad.get("description", ""))
                if desc:
                    return desc
            except (KeyError, TypeError):
                pass

        # JSON-LD
        if self._json_data.get("description"):
            return self._json_data["description"]

        # HTML - look for description section
        desc_selectors = [
            "[class*='description']",
            "[data-testid*='description']",
            "[class*='body']",
            ".u-word-break",
        ]
        for selector in desc_selectors:
            el = self.soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 20:  # skip tiny matches
                    return text

        # Try definition lists (classic Finn.no pattern)
        descriptions = []
        for dl in self.soup.find_all("dl"):
            for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                label = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                descriptions.append(f"{label}: {value}")

        return "\n".join(descriptions)

    def _get_price(self):
        """Extract price as integer."""
        # JSON-LD
        offers = self._json_data.get("offers", {})
        if isinstance(offers, dict) and offers.get("price"):
            try:
                return int(float(offers["price"]))
            except (ValueError, TypeError):
                pass

        # Next.js data
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                price = ad.get("price", {})
                if isinstance(price, dict):
                    val = price.get("amount") or price.get("value")
                    if val:
                        return int(float(val))
                elif isinstance(price, (int, float)):
                    return int(price)
            except (KeyError, TypeError, ValueError):
                pass

        # HTML
        price_selectors = [
            "[class*='price']",
            "[data-testid*='price']",
        ]
        for selector in price_selectors:
            el = self.soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                price = self._parse_price(text)
                if price:
                    return price

        return None

    def _get_location(self):
        """Extract location."""
        # Next.js data
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                loc = ad.get("location", {})
                if isinstance(loc, dict):
                    parts = []
                    for key in ["city", "name", "area", "region"]:
                        if loc.get(key):
                            parts.append(loc[key])
                    return ", ".join(parts)
                elif isinstance(loc, str):
                    return loc
            except (KeyError, TypeError):
                pass

        # HTML
        loc_selectors = [
            "[class*='location']",
            "[data-testid*='location']",
            "[class*='area']",
        ]
        for selector in loc_selectors:
            el = self.soup.select_one(selector)
            if el:
                return el.get_text(strip=True)

        return ""

    def _get_date_posted(self):
        """Extract posting date."""
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                return ad.get("published", ad.get("created", ""))
            except (KeyError, TypeError):
                pass

        # HTML - look for time element
        time_el = self.soup.find("time")
        if time_el:
            return time_el.get("datetime", time_el.get_text(strip=True))

        return ""

    def _get_seller_name(self):
        """Extract seller name."""
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                owner = ad.get("owner", ad.get("seller", {}))
                if isinstance(owner, dict):
                    return owner.get("name", "")
            except (KeyError, TypeError):
                pass

        # HTML
        seller_selectors = [
            "[class*='seller']",
            "[class*='owner']",
            "[class*='author']",
            "[data-testid*='seller']",
        ]
        for selector in seller_selectors:
            el = self.soup.select_one(selector)
            if el:
                return el.get_text(strip=True)

        return ""

    def _check_is_dealer(self):
        """Check if listing is from a dealer/forhandler."""
        text = self.soup.get_text().lower()
        dealer_indicators = [
            "forhandler",
            "bedrift",
            "butikk",
            "dealer",
            "forretning",
            "antikk",
            "antikkhandel",
        ]
        return any(indicator in text for indicator in dealer_indicators)

    def _check_is_active(self):
        """Check if listing is still active (not sold/inactive)."""
        text = self.soup.get_text().lower()
        inactive_indicators = ["solgt", "inaktiv", "fjernet", "utgått"]
        return not any(indicator in text for indicator in inactive_indicators)

    def _get_images(self):
        """Extract all image URLs from listing."""
        images = []

        # Next.js data
        if self._next_data:
            try:
                props = self._next_data["props"]["pageProps"]
                ad = props.get("ad", props.get("item", {}))
                imgs = ad.get("images", ad.get("photos", []))
                for img in imgs:
                    if isinstance(img, dict):
                        url = img.get("url") or img.get("src") or img.get("uri", "")
                        if url:
                            images.append(url)
                    elif isinstance(img, str):
                        images.append(img)
            except (KeyError, TypeError):
                pass

        if images:
            return images

        # HTML - look for finncdn.no images
        for img in self.soup.find_all("img", src=True):
            src = img["src"]
            if "finncdn.no" in src:
                images.append(src)

        # Also check data-src for lazy-loaded images
        for img in self.soup.find_all("img", attrs={"data-src": True}):
            src = img["data-src"]
            if "finncdn.no" in src:
                images.append(src)

        return list(dict.fromkeys(images))  # dedupe preserving order

    @staticmethod
    def _parse_price(text):
        """Parse price from text."""
        if not text:
            return None
        cleaned = text.lower().strip()
        cleaned = re.sub(r"(kr\.?|nok|,-)", "", cleaned)
        cleaned = re.sub(r"[\s\.]", "", cleaned)
        match = re.search(r"(\d+)", cleaned)
        if match:
            return int(match.group(1))
        return None
