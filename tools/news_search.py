import feedparser
from urllib.parse import quote
from difflib import SequenceMatcher


def normalize_title(title):
    """
    Normalize a title for duplicate detection.
    """
    title = title.lower()

    # Remove common punctuation
    for char in ".,!?;:'\"-–—()[]{}":
        title = title.replace(char, " ")

    # Remove extra spaces
    title = " ".join(title.split())

    return title


def is_similar_title(title1, title2, threshold=0.80):
    """
    Check whether two article titles are sufficiently similar.
    """

    t1 = normalize_title(title1)
    t2 = normalize_title(title2)

    similarity = SequenceMatcher(None, t1, t2).ratio()

    return similarity >= threshold


def search_news(topic, max_results=5):
    """
    Search Google News RSS and return unique article information.
    """

    encoded_topic = quote(topic)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    feed = feedparser.parse(url)

    articles = []

    # Get more candidates than we finally need.
    # This gives us room to remove duplicates.
    candidate_limit = max_results * 3

    for entry in feed.entries[:candidate_limit]:

        title = entry.get("title", "")
        google_url = entry.get("link", "")

        source = entry.get("source", {})

        if isinstance(source, dict):
            source_name = source.get("title", "")
            source_url = source.get("href", "")
        else:
            source_name = ""
            source_url = ""

        article = {
            "title": title,
            "url": google_url,
            "source": source_name,
            "source_url": source_url,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")
        }

        # -----------------------------------------
        # Duplicate detection
        # -----------------------------------------

        duplicate = False

        for existing in articles:

            if is_similar_title(
                article["title"],
                existing["title"]
            ):
                duplicate = True

                print(
                    f"\nDuplicate skipped:"
                    f"\n  {article['title']}"
                    f"\n  Similar to:"
                    f"\n  {existing['title']}"
                )

                break

        if not duplicate:

            articles.append(article)

            print(
                f"\nArticle accepted:"
                f"\n  {article['title']}"
                f"\n  Source: {article['source']}"
            )

        # Stop once we have enough unique articles
        if len(articles) >= max_results:
            break

    return articles


if __name__ == "__main__":

    articles = search_news(
        "artificial intelligence",
        max_results=5
    )

    print("\n" + "=" * 60)
    print("UNIQUE SEARCH RESULTS")
    print("=" * 60)

    for i, article in enumerate(articles, start=1):

        print(f"\n{i}. {article['title']}")
        print(f"Source: {article['source']}")
        print(f"Published: {article['published']}")
        print(f"URL: {article['url']}")