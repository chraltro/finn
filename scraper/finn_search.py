"""Core search and fetch logic for Finn.no.

Supports two modes:
1. requests + BeautifulSoup (default, fast, works for individual listings)
2. playwright (fallback for JS-rendered search pages)
"""

import json
import logging
import random
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlencode

import requests

from scraper.config import (
    DEFAULT_HEADERS,
    FINN_ITEM_URL,
    FINN_SEARCH_URL,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


@dataclass
class FinnListing:
    """Represents a single Finn.no listing."""

    finn_kode: str
    title: str
    price: Optional[int] = None
    price_text: str = ""
    description: str = ""
    location: str = ""
    url: str = ""
    image_urls: list = field(default_factory=list)
    date_posted: str = ""
    seller_name: str = ""
    is_dealer: bool = False
    is_active: bool = True
    search_query: str = ""
    raw_data: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d.pop("raw_data", None)
        return d


class FinnSearcher:
    """Handles searching and fetching from Finn.no."""

    def __init__(self, use_playwright=False):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.use_playwright = use_playwright
        self._playwright = None
        self._browser = None
        self._page = None

    def _delay(self):
        """Random delay between requests to be respectful."""
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    def search(self, query, max_pages=3, category=None):
        """Search Finn.no for listings matching query.

        Returns list of FinnListing with basic info (finn_kode, title, price, url).
        Individual listings need to be fetched separately for full details.
        """
        if self.use_playwright:
            return self._search_playwright(query, max_pages, category)
        return self._search_requests(query, max_pages, category)

    def _build_search_url(self, query, page=1, category=None):
        """Build a Finn.no search URL."""
        params = {
            "q": query,
            "sort": "PUBLISHED_DESC",
        }
        if category:
            params["category"] = category
        if page > 1:
            params["page"] = page
        return f"{FINN_SEARCH_URL}?{urlencode(params)}"

    def _search_requests(self, query, max_pages=3, category=None):
        """Search using requests + BeautifulSoup. Parses HTML for listing data."""
        from bs4 import BeautifulSoup

        all_listings = []

        for page in range(1, max_pages + 1):
            url = self._build_search_url(query, page, category)
            logger.info("Fetching search page: %s", url)

            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.warning("Failed to fetch search page %d for '%s': %s", page, query, e)
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to find embedded JSON data (Next.js __NEXT_DATA__ or similar)
            listings = self._extract_listings_from_json(soup, query)
            if listings:
                all_listings.extend(listings)
                logger.info("Found %d listings from JSON on page %d", len(listings), page)
            else:
                # Fall back to HTML parsing
                listings = self._extract_listings_from_html(soup, query)
                all_listings.extend(listings)
                logger.info("Found %d listings from HTML on page %d", len(listings), page)

            if not listings:
                logger.info("No more listings found, stopping pagination")
                break

            self._delay()

        return all_listings

    def _extract_listings_from_json(self, soup, query):
        """Try to extract listing data from embedded JSON in the page."""
        listings = []

        # Look for __NEXT_DATA__ script tag (Next.js pattern)
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            try:
                data = json.loads(script.string)
                return self._parse_next_data(data, query)
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug("Failed to parse __NEXT_DATA__: %s", e)

        # Look for any script tag containing search result data
        for script in soup.find_all("script"):
            if not script.string:
                continue
            text = script.string
            # Look for common patterns of embedded data
            for pattern in [
                r'window\.__data__\s*=\s*({.+?});',
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'"docs"\s*:\s*(\[.+?\])',
            ]:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        parsed = self._parse_embedded_data(data, query)
                        if parsed:
                            return parsed
                    except (json.JSONDecodeError, KeyError):
                        continue

        return listings

    def _parse_next_data(self, data, query):
        """Parse Next.js embedded data for listings."""
        listings = []
        try:
            # Navigate the Next.js data structure
            # The exact path depends on Finn.no's implementation
            props = data.get("props", {}).get("pageProps", {})

            # Try common patterns for search results
            search_data = (
                props.get("searchResult", {})
                or props.get("search", {})
                or props.get("data", {})
            )

            docs = (
                search_data.get("docs", [])
                or search_data.get("items", [])
                or search_data.get("ads", [])
            )

            for doc in docs:
                listing = self._doc_to_listing(doc, query)
                if listing:
                    listings.append(listing)
        except (AttributeError, TypeError) as e:
            logger.debug("Error parsing Next.js data: %s", e)

        return listings

    def _parse_embedded_data(self, data, query):
        """Parse generic embedded JSON data for listings."""
        listings = []
        items = data if isinstance(data, list) else data.get("docs", data.get("items", []))
        for item in items:
            listing = self._doc_to_listing(item, query)
            if listing:
                listings.append(listing)
        return listings

    def _doc_to_listing(self, doc, query):
        """Convert a JSON document/dict to a FinnListing."""
        if not isinstance(doc, dict):
            return None

        finn_kode = str(
            doc.get("id", "")
            or doc.get("ad_id", "")
            or doc.get("finnkode", "")
            or doc.get("code", "")
        )
        if not finn_kode:
            return None

        title = doc.get("heading", "") or doc.get("title", "") or doc.get("subject", "")

        # Extract price
        price = None
        price_text = ""
        price_data = doc.get("price", doc.get("main_price", {}))
        if isinstance(price_data, dict):
            price = price_data.get("amount") or price_data.get("value")
            price_text = price_data.get("text", str(price) if price else "")
        elif isinstance(price_data, (int, float)):
            price = int(price_data)
            price_text = str(price)
        elif isinstance(price_data, str):
            price_text = price_data
            price = self._parse_price_text(price_data)

        # Extract location
        location = ""
        loc_data = doc.get("location", doc.get("area", ""))
        if isinstance(loc_data, dict):
            location = loc_data.get("name", "") or loc_data.get("city", "")
        elif isinstance(loc_data, str):
            location = loc_data

        # Extract images
        image_urls = []
        images = doc.get("images", doc.get("image", []))
        if isinstance(images, list):
            for img in images:
                if isinstance(img, dict):
                    image_urls.append(img.get("url", "") or img.get("src", ""))
                elif isinstance(img, str):
                    image_urls.append(img)
        elif isinstance(images, dict):
            image_urls.append(images.get("url", "") or images.get("src", ""))

        url = doc.get("ad_link", "") or doc.get("url", "")
        if not url and finn_kode:
            url = FINN_ITEM_URL.format(finn_kode=finn_kode)

        return FinnListing(
            finn_kode=finn_kode,
            title=title,
            price=int(price) if price else None,
            price_text=price_text,
            location=location,
            url=url,
            image_urls=[u for u in image_urls if u],
            search_query=query,
            raw_data=doc,
        )

    def _extract_listings_from_html(self, soup, query):
        """Extract listings from HTML search results page."""
        listings = []

        # Finn.no uses article elements or ad-card components for listings
        # Try multiple selector patterns since the site structure may change
        selectors = [
            "article[class*='ad']",
            "article[class*='result']",
            "[class*='AdCard']",
            "[class*='ad-card']",
            "a[class*='ad-link']",
            "[data-testid*='ad']",
            "article",
        ]

        ads = []
        for selector in selectors:
            ads = soup.select(selector)
            if ads:
                logger.debug("Found ads with selector: %s", selector)
                break

        for ad in ads:
            listing = self._parse_ad_element(ad, query)
            if listing:
                listings.append(listing)

        return listings

    def _parse_ad_element(self, element, query):
        """Parse a single ad HTML element into a FinnListing."""
        # Extract finn_kode from link href
        finn_kode = ""
        link = element.find("a", href=True) if element.name != "a" else element
        if link and link.get("href"):
            href = link["href"]
            # Match /item/12345 or finn_kode=12345 patterns
            match = re.search(r"/item/(\d+)", href) or re.search(r"finnkode=(\d+)", href)
            if match:
                finn_kode = match.group(1)

        if not finn_kode:
            # Try data attributes
            finn_kode = (
                element.get("data-finnkode", "")
                or element.get("data-ad-id", "")
                or element.get("id", "")
            )
            # Clean non-numeric
            finn_kode = re.sub(r"\D", "", str(finn_kode))

        if not finn_kode:
            return None

        # Extract title
        title = ""
        title_el = (
            element.find(["h2", "h3"])
            or element.find(class_=re.compile(r"heading|title", re.I))
        )
        if title_el:
            title = title_el.get_text(strip=True)

        # Extract price
        price_text = ""
        price = None
        price_el = element.find(class_=re.compile(r"price", re.I))
        if price_el:
            price_text = price_el.get_text(strip=True)
            price = self._parse_price_text(price_text)

        # Extract location
        location = ""
        loc_el = element.find(class_=re.compile(r"location|area", re.I))
        if loc_el:
            location = loc_el.get_text(strip=True)

        # Extract image
        image_urls = []
        img = element.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                image_urls.append(src)

        url = FINN_ITEM_URL.format(finn_kode=finn_kode)

        return FinnListing(
            finn_kode=finn_kode,
            title=title,
            price=price,
            price_text=price_text,
            location=location,
            url=url,
            image_urls=image_urls,
            search_query=query,
        )

    def fetch_listing_details(self, listing):
        """Fetch full details for a single listing page.

        Updates the listing in-place with description, seller info, etc.
        """
        url = listing.url or FINN_ITEM_URL.format(finn_kode=listing.finn_kode)
        logger.info("Fetching listing details: %s", url)

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Failed to fetch listing %s: %s", listing.finn_kode, e)
            return listing

        from scraper.finn_parser import FinnListingParser

        parser = FinnListingParser(resp.text)
        parser.update_listing(listing)

        self._delay()
        return listing

    def _search_playwright(self, query, max_pages=3, category=None):
        """Search using Playwright for JS-rendered content."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "Playwright not installed. Install with: pip install playwright && python -m playwright install chromium"
            )
            return []

        listings = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=DEFAULT_HEADERS["User-Agent"],
                locale="nb-NO",
            )

            for page_num in range(1, max_pages + 1):
                url = self._build_search_url(query, page_num, category)
                logger.info("Playwright fetching: %s", url)

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    # Wait for ad cards to render
                    page.wait_for_selector(
                        "article, [class*='ad'], [class*='AdCard']",
                        timeout=10000,
                    )
                except Exception as e:
                    logger.warning("Playwright failed on page %d: %s", page_num, e)
                    break

                # Extract page content and parse
                content = page.content()
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(content, "html.parser")

                # Try JSON first, then HTML
                page_listings = self._extract_listings_from_json(soup, query)
                if not page_listings:
                    page_listings = self._extract_listings_from_html(soup, query)

                if not page_listings:
                    break

                listings.extend(page_listings)
                logger.info(
                    "Found %d listings on page %d (Playwright)", len(page_listings), page_num
                )
                self._delay()

            browser.close()

        return listings

    @staticmethod
    def _parse_price_text(text):
        """Parse a Norwegian price string into an integer.

        Handles formats like:
        - '2 500 kr'
        - '2.500,-'
        - '2500'
        - 'Kr 2 500'
        - '2 500 NOK'
        """
        if not text:
            return None
        # Remove common suffixes/prefixes
        cleaned = text.lower().strip()
        cleaned = re.sub(r"(kr\.?|nok|,-)", "", cleaned)
        # Remove spaces and dots used as thousand separators
        cleaned = re.sub(r"[\s\.]", "", cleaned)
        # Extract digits
        match = re.search(r"(\d+)", cleaned)
        if match:
            return int(match.group(1))
        return None
