import re
from tools.news_search import search_news
from tools.article_reader import read_article
from tools.summarizer import SummarizationError, summarize_article
from tools.storage import DB_PATH, save_article


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "into", "is", "of", "on", "or", "the", "to", "with",
}
_CONCEPT_ALIASES = (
    (re.compile(r"\bartificial\s+intelligence\b"), "ai"),
    (re.compile(r"\ba\.?\s*i\.?\b"), "ai"),
    (re.compile(r"\bmachine\s+learning\b"), "ml"),
    (re.compile(r"\bnatural\s+language\s+processing\b"), "nlp"),
    (re.compile(r"\blarge\s+language\s+models?\b"), "llm"),
)


def _topic_terms(text):
    """Normalize common multiword concepts and return meaningful unique terms."""
    normalized = text.lower()
    for pattern, replacement in _CONCEPT_ALIASES:
        normalized = pattern.sub(f" {replacement} ", normalized)

    return {
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if token not in _STOP_WORDS and (len(token) > 1 or token in {"ai", "ml"})
    }


def calculate_similarity(topic, text, title=""):
    """
    Calculate topic-term coverage across the article and its headline.
    """
    topic_terms = _topic_terms(topic)
    if not topic_terms or not (text or title):
        return 0.0

    article_terms = _topic_terms(f"{title} {text or ''}")
    return len(topic_terms & article_terms) / len(topic_terms)

def run_agent(topic, max_articles=5, min_similarity=0.5, db_path=DB_PATH):
    print(f"--- Fetching news for topic: {topic} ---")
    candidates = search_news(topic, max_results=15)
    
    summarized_articles = []

    for item in candidates:
        if len(summarized_articles) >= max_articles:
            break

        print(f"\nProcessing: {item['title']}")
        text = read_article(item['url'])
        
        if not text:
            print("Skipping: Text extraction returned None.")
            continue

        # Score relevance against topic
        relevance_score = calculate_similarity(topic, text, item["title"])
        print(f"Relevance Score (topic-term coverage): {round(relevance_score, 3)}")

        if relevance_score >= min_similarity:
            print("Score threshold met. Summarizing...")
            try:
                summary = summarize_article(
                    article_text=text,
                    title=item['title'],
                    source=item['source'],
                    published=item['published']
                )
            except SummarizationError as exc:
                print(f"Summarization failed: {exc} Skipping article.")
                if exc.status_code in {401, 402, 404}:
                    print(
                        "Stopping summary generation for this run because the "
                        "API configuration or service budget is unavailable."
                    )
                    break
                continue

            if (
                not isinstance(summary, dict)
                or not isinstance(summary.get("summary"), str)
                or not summary["summary"].strip()
            ):
                print("Summarization failed: model returned no structured summary; skipping article.")
                continue

            article = {
                "title": item['title'],
                **summary,
                "url": item["url"],
                "source": item["source"],
                "published": item["published"],
                "score": relevance_score,
            }
            save_article(article, db_path=db_path)
            summarized_articles.append(article)
        else:
            print("Skipping: Similarity score below threshold.")

    return summarized_articles

if __name__ == "__main__":
    topic_query = input("Enter research topic: ")
    results = run_agent(topic_query)
    
    print("\n" + "="*60)
    print("FINAL SUMMARIES")
    print("="*60)
    for idx, res in enumerate(results, start=1):
        print(f"\n--- Article {idx} (Relevance: {res['score']:.2f}) ---")
        print(res["headline"])
        print(res['summary'])
        print("Key points:")
        for point in res["key_points"]:
            print(f"- {point}")
        print(f"Key takeaway: {res['key_takeaway']}")