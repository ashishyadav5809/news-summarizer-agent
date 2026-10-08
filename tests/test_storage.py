import tempfile
import unittest
from pathlib import Path

from tools.storage import list_articles, save_article


def _article(summary="A concise summary."):
    return {
        "url": "https://example.com/article",
        "title": "Example headline",
        "source": "Example",
        "published": "Today",
        "score": 0.75,
        "headline": "A concise headline",
        "summary": summary,
        "key_points": ["First point", "Second point"],
        "key_takeaway": "The main takeaway.",
    }


class ArticleStorageTests(unittest.TestCase):
    def test_saves_and_reads_structured_article_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "data" / "news.db"

            save_article(_article(), db_path=db_path)
            articles = list_articles(db_path=db_path)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], "https://example.com/article")
        self.assertEqual(articles[0]["key_points"], ["First point", "Second point"])
        self.assertEqual(articles[0]["score"], 0.75)

    def test_updates_existing_article_by_url_instead_of_duplicating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "news.db"

            save_article(_article(), db_path=db_path)
            save_article(_article("Updated summary."), db_path=db_path)
            articles = list_articles(db_path=db_path)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["summary"], "Updated summary.")

    def test_rejects_articles_without_a_url(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "URL is required"):
                save_article({"title": "Missing URL"}, db_path=Path(directory) / "news.db")


if __name__ == "__main__":
    unittest.main()
