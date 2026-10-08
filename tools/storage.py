import json
import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "news.db"


def initialize_database(db_path=DB_PATH):
    """Create the saved-article table if it does not already exist."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    headline TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_points TEXT NOT NULL,
                    key_takeaway TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def save_article(article, db_path=DB_PATH):
    """Insert an article or refresh its saved summary when its URL already exists."""
    url = article.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A non-empty article URL is required for storage.")

    initialize_database(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO articles (
                    url, title, source, published, relevance_score, headline,
                    summary, key_points, key_takeaway
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    source = excluded.source,
                    published = excluded.published,
                    relevance_score = excluded.relevance_score,
                    headline = excluded.headline,
                    summary = excluded.summary,
                    key_points = excluded.key_points,
                    key_takeaway = excluded.key_takeaway,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    url.strip(),
                    article["title"],
                    article["source"],
                    article["published"],
                    article["score"],
                    article["headline"],
                    article["summary"],
                    json.dumps(article["key_points"], ensure_ascii=False),
                    article["key_takeaway"],
                ),
            )


def list_articles(limit=20, db_path=DB_PATH):
    """Return saved articles, newest first, with key points decoded as a list."""
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("Article limit must be a positive integer.")

    initialize_database(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT url, title, source, published, relevance_score AS score,
                   headline, summary, key_points, key_takeaway, created_at,
                   updated_at
            FROM articles
            ORDER BY created_at DESC, url
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    articles = []
    for row in rows:
        article = dict(row)
        article["key_points"] = json.loads(article["key_points"])
        articles.append(article)
    return articles
