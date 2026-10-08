import feedparser

from difflib import SequenceMatcher

import base64

import requests

from bs4 import BeautifulSoup

from urllib.parse import (
    urlparse,
    parse_qs,
    unquote,
    quote
)

from playwright.sync_api import sync_playwright


# ============================================================
# DOMAIN UTILITIES
# ============================================================


def normalize_domain(url):
    """
    Extract and normalize domain from a URL.
    """

    if not url:
        return ""

    try:
        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def clean_title(title):
    """
    Remove publisher/domain suffixes from article titles.
    """

    if not title:
        return ""

    cleaned = title.strip()

    suffixes = [

        " - theatlantic.com",
        " | theatlantic.com",
        " - The Atlantic",
        " | The Atlantic",

        " - reuters.com",
        " | reuters.com",
        " - Reuters",
        " | Reuters",

        " - ndtv.com",
        " | ndtv.com",
        " - NDTV",
        " | NDTV",

        " - independent.co.uk",
        " | independent.co.uk",
        " - The Independent",
        " | The Independent",

        " - wsj.com",
        " | wsj.com",
        " - WSJ",
        " | WSJ",
    ]

    changed = True

    while changed:

        changed = False

        for suffix in suffixes:

            if cleaned.lower().endswith(
                suffix.lower()
            ):

                cleaned = cleaned[
                    : -len(suffix)
                ].strip()

                changed = True

                break

    return cleaned


# ============================================================
# BING REDIRECT DECODER
# ============================================================


def decode_bing_url(url):
    """
    Convert a Bing redirect URL such as:

        https://www.bing.com/ck/a?...&u=a1aHR0...

    into the real destination URL.
    """

    if not url:
        return None

    try:

        parsed = urlparse(url)

        # Already a normal URL
        if "bing.com" not in parsed.netloc.lower():
            return url

        query = parse_qs(
            parsed.query
        )

        encoded_values = query.get("u")

        if not encoded_values:
            return None

        encoded = encoded_values[0]

        # Bing usually stores:
        #
        # u=a1 + base64(...)
        #

        if encoded.startswith("a1"):

            encoded = encoded[2:]

            # Add missing padding
            padding = len(encoded) % 4

            if padding:
                encoded += "=" * (
                    4 - padding
                )

            try:

                decoded = base64.urlsafe_b64decode(
                    encoded
                ).decode(
                    "utf-8",
                    errors="ignore"
                )

                if decoded.startswith("http"):
                    return decoded

            except Exception:
                pass

        # Sometimes URL is simply URL encoded
        decoded = unquote(
            encoded
        )

        if decoded.startswith("http"):
            return decoded

    except Exception as e:

        print(
            "Bing URL decode error:",
            e
        )

    return None


# ============================================================
# URL VALIDATION
# ============================================================


def is_valid_article_url(
    url,
    publisher_domain
):
    """
    Check whether URL belongs to publisher
    and looks like an article page.
    """

    if not url:
        return False

    try:

        parsed = urlparse(url)

        domain = normalize_domain(
            url
        )

        if not domain:
            return False

        # ----------------------------------------------------
        # Publisher check
        # ----------------------------------------------------

        if publisher_domain:

            if not (
                domain == publisher_domain
                or domain.endswith(
                    "." + publisher_domain
                )
            ):

                return False

        # ----------------------------------------------------
        # Ignore search engines
        # ----------------------------------------------------

        blocked_domains = [

            "bing.com",
            "google.com",
            "duckduckgo.com",
            "yahoo.com",
            "news.google.com"

        ]

        if any(
            blocked in domain
            for blocked in blocked_domains
        ):

            return False

        # ----------------------------------------------------
        # Ignore obvious non-article pages
        # ----------------------------------------------------

        path = parsed.path.lower()

        bad_patterns = [

            "/search",
            "/tag/",
            "/tags/",
            "/category/",
            "/categories/",
            "/author/",
            "/authors/",
            "/topic/",
            "/topics/",
            "/about",
            "/contact",
            "/login",
            "/subscribe",
            "/newsletters",
            "/podcasts",
            "/projects/",
            "/live/",
            "/video/",
            "/videos/",
            "/gallery/"

        ]

        if any(
            pattern in path
            for pattern in bad_patterns
        ):

            return False

        # ----------------------------------------------------
        # Must have a meaningful path
        # ----------------------------------------------------

        if not path or path == "/":
            return False

        return True

    except Exception:

        return False


# ============================================================
# GOOGLE NEWS URL RESOLUTION USING PLAYWRIGHT
# ============================================================


def resolve_google_news_with_playwright(
    google_news_url,
    publisher_domain,
    browser
):
    """
    Resolve a Google News article URL using Playwright.

    Google News URLs can look like:

        https://news.google.com/rss/articles/CBMi...

    Requests may leave us on the Google News wrapper.

    Playwright gives Chromium a chance to perform the
    same browser-side navigation that a normal browser uses.

    Strategy:

        Google News URL
              ↓
        Chromium navigation
              ↓
        Check final URL
              ↓
        Inspect page links
              ↓
        Validate publisher URL
    """

    if not google_news_url:
        return None

    page = None

    try:

        print(
            "\nPlaywright resolving Google News URL:"
        )

        print(google_news_url)

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/154.0.0.0 "
                "Safari/537.36"
            ),
            locale="en-US"
        )

        page.set_default_timeout(15000)

        # ----------------------------------------------------
        # Navigate to Google News article
        # ----------------------------------------------------

        page.goto(
            google_news_url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        # Give redirects / client-side navigation time
        page.wait_for_timeout(3000)

        # ----------------------------------------------------
        # Check final browser URL
        # ----------------------------------------------------

        final_url = page.url

        print(
            "Playwright final URL:",
            final_url
        )

        if is_valid_article_url(
            final_url,
            publisher_domain
        ):

            print(
                "\nPlaywright resolved "
                "publisher article:"
            )

            print(final_url)

            return final_url

        # ----------------------------------------------------
        # Inspect page links
        # ----------------------------------------------------

        print(
            "Browser remained on Google News."
        )

        print(
            "Searching page for publisher links..."
        )

        links = page.locator("a")

        try:
            count = links.count()
        except Exception:
            count = 0

        print(
            "Links found:",
            count
        )

        for i in range(count):

            try:

                href = links.nth(
                    i
                ).get_attribute(
                    "href"
                )

                if not href:
                    continue

                href = href.strip()

                # Convert relative Google News URLs
                if href.startswith("/"):

                    href = (
                        "https://news.google.com"
                        + href
                    )

                # Some links may be HTML encoded
                href = unquote(href)

                print(
                    "Checking link:",
                    href
                )

                if is_valid_article_url(
                    href,
                    publisher_domain
                ):

                    print(
                        "\nPublisher article "
                        "link found:"
                    )

                    print(href)

                    return href

            except Exception:
                continue

        # ----------------------------------------------------
        # Look for canonical URL
        # ----------------------------------------------------

        try:

            canonical = page.locator(
                'link[rel="canonical"]'
            ).get_attribute(
                "href"
            )

            if canonical:

                canonical = unquote(
                    canonical.strip()
                )

                print(
                    "Canonical URL:",
                    canonical
                )

                if is_valid_article_url(
                    canonical,
                    publisher_domain
                ):

                    print(
                        "\nCanonical publisher "
                        "article found:"
                    )

                    print(canonical)

                    return canonical

        except Exception:
            pass

        # ----------------------------------------------------
        # Look for Open Graph URL
        # ----------------------------------------------------

        try:

            og_url = page.locator(
                'meta[property="og:url"]'
            ).get_attribute(
                "content"
            )

            if og_url:

                og_url = unquote(
                    og_url.strip()
                )

                print(
                    "OG URL:",
                    og_url
                )

                if is_valid_article_url(
                    og_url,
                    publisher_domain
                ):

                    print(
                        "\nOG publisher "
                        "article found:"
                    )

                    print(og_url)

                    return og_url

        except Exception:
            pass

        return None

    except Exception as e:

        print(
            "Playwright Google News "
            "resolution error:",
            e
        )

        return None

    finally:

        if page:

            try:
                page.close()
            except Exception:
                pass


# ============================================================
# BING SEARCH
# ============================================================


def search_bing(
    title,
    publisher_domain
):
    """
    Search Bing using the normal HTTP interface.

    Bing often returns redirect URLs.
    Those are decoded before validation.
    """

    query = (
        f'"{title}" '
        f'site:{publisher_domain}'
    )

    print("\nBing search:")
    print(query)

    search_url = (
        "https://www.bing.com/search?q="
        + quote(query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0.0.0 "
            "Safari/537.36"
        ),
        "Accept-Language":
            "en-US,en;q=0.9"
    }

    try:

        response = requests.get(
            search_url,
            headers=headers,
            timeout=20
        )

        print(
            "Bing status:",
            response.status_code
        )

        response.raise_for_status()

    except requests.RequestException as e:

        print(
            "Bing request failed:",
            e
        )

        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = soup.select(
        "li.b_algo"
    )

    print(
        "Bing results found:",
        len(results)
    )

    for result in results:

        link = result.select_one(
            "h2 a"
        )

        if not link:
            continue

        href = link.get(
            "href"
        )

        result_title = link.get_text(
            " ",
            strip=True
        )

        if not href:
            continue

        print("\nCandidate:")

        print(
            "Title:",
            result_title
        )

        print(
            "Raw URL:",
            href
        )

        # ----------------------------------------------------
        # Decode Bing redirect
        # ----------------------------------------------------

        real_url = decode_bing_url(
            href
        )

        if not real_url:

            # It may already be a direct URL
            real_url = href

        print(
            "Decoded URL:",
            real_url
        )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if not is_valid_article_url(
            real_url,
            publisher_domain
        ):

            print(
                "Rejected: not a valid "
                "publisher article."
            )

            continue

        print(
            "\nBing article URL found:"
        )

        print(real_url)

        return real_url

    return None


# ============================================================
# DUCKDUCKGO SEARCH
# ============================================================


def search_duckduckgo(
    title,
    publisher_domain
):
    """
    Fallback search using DuckDuckGo HTML.
    """

    query = (
        f'"{title}" '
        f'site:{publisher_domain}'
    )

    print("\nDuckDuckGo search:")
    print(query)

    search_url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0.0.0 "
            "Safari/537.36"
        ),
        "Accept-Language":
            "en-US,en;q=0.9"
    }

    try:

        response = requests.get(
            search_url,
            headers=headers,
            timeout=20
        )

        print(
            "DuckDuckGo status:",
            response.status_code
        )

        response.raise_for_status()

    except requests.RequestException as e:

        print(
            "DuckDuckGo request failed:",
            e
        )

        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = soup.select(
        ".result"
    )

    print(
        "DuckDuckGo results found:",
        len(results)
    )

    for result in results:

        link = result.select_one(
            ".result__a"
        )

        if not link:
            continue

        href = link.get(
            "href"
        )

        result_title = link.get_text(
            " ",
            strip=True
        )

        if not href:
            continue

        print("\nCandidate:")

        print(
            "Title:",
            result_title
        )

        print(
            "URL:",
            href
        )

        if not is_valid_article_url(
            href,
            publisher_domain
        ):

            print(
                "Rejected."
            )

            continue

        print(
            "\nDuckDuckGo article URL found:"
        )

        print(href)

        return href

    return None


# ============================================================
# GOOGLE NEWS RSS RESOLUTION
# ============================================================


def resolve_from_google_news(
    title,
    publisher_domain
):
    """
    Resolve an article using Google News RSS.

    Strategy:

        title
            ↓
        Google News RSS search
            ↓
        matching article
            ↓
        Google News article URL
            ↓
        Playwright / Chromium
            ↓
        actual publisher URL
    """

    print("\nGoogle News RSS search:")

    rss_query = title

    rss_url = (
        "https://news.google.com/rss/search?"
        f"q={quote(rss_query)}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )

    print(
        "Google News RSS URL:",
        rss_url
    )

    try:

        feed = feedparser.parse(
            rss_url
        )

    except Exception as e:

        print(
            "Google News RSS error:",
            e
        )

        return None

    print(
        "Google News results found:",
        len(feed.entries)
    )

    if not feed.entries:
        return None

    cleaned_target = clean_title(
        title
    ).lower().strip()

    # --------------------------------------------------------
    # Start Playwright once.
    #
    # The same Chromium instance is reused for all candidates.
    # --------------------------------------------------------

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            try:

                # ------------------------------------------------
                # First collect and score candidates.
                # ------------------------------------------------

                candidates = []

                for entry in feed.entries:

                    entry_title = entry.get(
                        "title",
                        ""
                    ).strip()

                    entry_url = entry.get(
                        "link",
                        ""
                    ).strip()

                    if not entry_title or not entry_url:
                        continue

                    print(
                        "\nGoogle News candidate:"
                    )

                    print(
                        "Title:",
                        entry_title
                    )

                    print(
                        "URL:",
                        entry_url
                    )

                    # --------------------------------------------
                    # Remove publisher suffix
                    # --------------------------------------------

                    candidate_title = clean_title(
                        entry_title
                    ).lower().strip()

                    # --------------------------------------------
                    # Calculate title similarity
                    # --------------------------------------------

                    score = SequenceMatcher(
                        None,
                        cleaned_target,
                        candidate_title
                    ).ratio()

                    print(
                        "Title similarity:",
                        round(score, 3)
                    )

                    # --------------------------------------------
                    # Publisher check from RSS metadata
                    # --------------------------------------------

                    source = entry.get(
                        "source",
                        {}
                    )

                    source_title = ""

                    if hasattr(
                        source,
                        "get"
                    ):

                        source_title = source.get(
                            "title",
                            ""
                        )

                    source_title = (
                        source_title or ""
                    ).lower()

                    publisher_match = (
                        publisher_domain.lower()
                        in source_title
                    )

                    candidates.append(
                        (
                            score,
                            publisher_match,
                            entry_url,
                            entry_title
                        )
                    )

                # ------------------------------------------------
                # Sort candidates.
                #
                # Exact title matches come first.
                # Publisher metadata is used as a secondary
                # signal.
                # ------------------------------------------------

                candidates.sort(
                    key=lambda item: (
                        item[0],
                        item[1]
                    ),
                    reverse=True
                )

                # ------------------------------------------------
                # Try the strongest candidates first.
                #
                # Limiting the number prevents opening dozens of
                # browser pages when Google News returns a large
                # feed.
                # ------------------------------------------------

                max_candidates = min(
                    len(candidates),
                    10
                )

                for (
                    score,
                    publisher_match,
                    entry_url,
                    entry_title
                ) in candidates[:max_candidates]:

                    print(
                        "\n------------------------------------------------"
                    )

                    print(
                        "Trying Google News candidate:"
                    )

                    print(
                        "Title:",
                        entry_title
                    )

                    print(
                        "Similarity:",
                        round(score, 3)
                    )

                    print(
                        "Publisher metadata match:",
                        publisher_match
                    )

                    print(
                        "URL:",
                        entry_url
                    )

                    # ------------------------------------------------
                    # Playwright resolution
                    # ------------------------------------------------

                    final_url = (
                        resolve_google_news_with_playwright(
                            entry_url,
                            publisher_domain,
                            browser
                        )
                    )

                    if not final_url:

                        print(
                            "Playwright could not "
                            "resolve this candidate."
                        )

                        continue

                    # ------------------------------------------------
                    # Final publisher validation
                    # ------------------------------------------------

                    final_domain = normalize_domain(
                        final_url
                    )

                    actual_publisher_match = (
                        final_domain == publisher_domain
                        or final_domain.endswith(
                            "." + publisher_domain
                        )
                    )

                    if not actual_publisher_match:

                        print(
                            "Rejected: resolved URL "
                            "does not belong to publisher."
                        )

                        continue

                    # ------------------------------------------------
                    # Strong title match
                    # ------------------------------------------------

                    if (
                        score >= 0.55
                        or publisher_match
                    ):

                        print(
                            "\nGoogle News resolved "
                            "publisher article:"
                        )

                        print(final_url)

                        return final_url

                print(
                    "\nGoogle News RSS could not "
                    "resolve the article."
                )

                return None

            finally:

                browser.close()

    except Exception as e:

        print(
            "\nCould not start/use Playwright:",
            e
        )

        print(
            "Make sure Playwright Chromium "
            "is installed with:"
        )

        print(
            "python -m playwright install chromium"
        )

        return None


# ============================================================
# MAIN RESOLVER
# ============================================================


def resolve_article_url(
    title,
    publisher_url=None
):
    """
    Resolve a news article title into
    the actual publisher article URL.

    Strategy:

        1. Clean title

        2. Search Google News RSS

        3. Resolve Google News URL using Playwright

        4. Validate publisher URL

        5. Search Bing if needed

        6. Decode Bing redirect

        7. Validate publisher URL

        8. Search DuckDuckGo if needed

        9. Return None if unresolved
    """

    if not title:

        print(
            "No article title provided."
        )

        return None

    publisher_domain = None

    if publisher_url:

        publisher_domain = normalize_domain(
            publisher_url
        )

    if not publisher_domain:

        print(
            "Publisher domain could not "
            "be determined."
        )

        return None

    cleaned_title = clean_title(
        title
    )

    print(
        "\nTrying article URL resolution..."
    )

    print(
        "Publisher domain:",
        publisher_domain
    )

    print(
        "Original title:",
        title
    )

    print(
        "Cleaned title:",
        cleaned_title
    )

    # ========================================================
    # STEP 1 — GOOGLE NEWS RSS + PLAYWRIGHT
    # ========================================================

    print(
        "\nTrying Google News RSS + Playwright..."
    )

    result = resolve_from_google_news(
        cleaned_title,
        publisher_domain
    )

    if result:

        print(
            "\nArticle successfully "
            "resolved using Google News "
            "and Playwright."
        )

        return result

    # ========================================================
    # STEP 2 — BING
    # ========================================================

    print(
        "\nGoogle News RSS + Playwright "
        "could not resolve the article."
    )

    print(
        "Trying Bing..."
    )

    result = search_bing(
        cleaned_title,
        publisher_domain
    )

    if result:

        print(
            "\nArticle successfully "
            "resolved using Bing."
        )

        return result

    # ========================================================
    # STEP 3 — DUCKDUCKGO
    # ========================================================

    print(
        "\nBing could not resolve article."
    )

    print(
        "Trying DuckDuckGo..."
    )

    result = search_duckduckgo(
        cleaned_title,
        publisher_domain
    )

    if result:

        print(
            "\nArticle successfully "
            "resolved using DuckDuckGo."
        )

        return result

    # ========================================================
    # STEP 4 — FAILURE
    # ========================================================

    print(
        "\nCould not resolve publisher "
        "article URL."
    )

    print(
        "The caller should use the "
        "RSS fallback."
    )

    return None


# ============================================================
# TEST
# ============================================================


if __name__ == "__main__":

    title = input(
        "Enter article title: "
    )

    publisher_url = input(
        "Enter publisher URL: "
    )

    result = resolve_article_url(
        title,
        publisher_url
    )

    if result:

        print(
            "\nArticle URL resolved:"
        )

        print(result)

    else:

        print(
            "\nArticle URL could not "
            "be resolved."
        )