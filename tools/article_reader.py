import requests
import trafilatura

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:
    try:
        from googlenewsdecoder import new_decodurl as gnewsdecoder
    except ImportError:
        gnewsdecoder = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def _decode_google_news_url(url):
    """Decode Google News URLs across both legacy and current googlenewsdecoder APIs."""
    if not url or "news.google.com" not in url or gnewsdecoder is None:
        return url

    try:
        decoded = gnewsdecoder(url)

        if isinstance(decoded, list):
            decoded = decoded[0] if decoded else {}

        if isinstance(decoded, dict):
            if decoded.get("decoded_url") and decoded.get("success") is not False:
                return decoded["decoded_url"]
            if decoded.get("status") and decoded.get("decoded_url"):
                return decoded["decoded_url"]
    except Exception as exc:
        print(f"URL Decoding failed: {exc}")

    return url


def _browser_fallback(url):
    """Use a real browser when request-based fetching is blocked or returns no text."""
    if not url or sync_playwright is None:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1800},
            )
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()

            text = trafilatura.extract(html, include_comments=False, favor_precision=True)
            if text:
                return text
    except Exception as exc:
        print(f"Browser fallback failed for {url}: {exc}")

    return None


def read_article(url):
    """
    Decodes Google News URLs and extracts article content using trafilatura.
    """
    final_url = _decode_google_news_url(url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(final_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        text = trafilatura.extract(response.text, include_comments=False, favor_precision=True)
        if text:
            return text

        print(f"No text extracted from {final_url} via HTTP; trying browser fallback.")
        return _browser_fallback(final_url)

    except requests.RequestException as e:
        print(f"Request failed for {final_url}: {e}. Trying browser fallback.")
        return _browser_fallback(final_url)
