import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from main import calculate_similarity, run_agent
from tools.summarizer import SummarizationError
from tools.storage import list_articles


def _summary(summary="Completed summary."):
    return {
        "headline": "Article headline",
        "source": "Example",
        "published": "Today",
        "summary": summary,
        "key_points": ["An important point."],
        "key_takeaway": "The main takeaway.",
    }


class CalculateSimilarityTests(unittest.TestCase):
    def test_matches_ai_abbreviation_to_full_phrase(self):
        self.assertEqual(
            calculate_similarity(
                "artificial intelligence",
                "The article discusses AI and its effects on work.",
            ),
            1.0,
        )

    def test_uses_title_and_full_article_text(self):
        self.assertEqual(
            calculate_similarity(
                "AI healthcare",
                "The article covers developments in medicine.",
                title="AI systems are changing healthcare",
            ),
            1.0,
        )

    def test_scores_partial_topic_coverage(self):
        self.assertEqual(
            calculate_similarity("AI healthcare", "AI adoption is growing."),
            0.5,
        )

    def test_returns_zero_for_empty_topic_or_article(self):
        self.assertEqual(calculate_similarity("", "Article text"), 0.0)
        self.assertEqual(calculate_similarity("artificial intelligence", ""), 0.0)

    def test_does_not_add_an_empty_model_response_as_a_summary(self):
        article = {
            "title": "Global update",
            "url": "https://example.com/article",
            "source": "Example",
            "published": "Today",
        }
        output = io.StringIO()
        with (
            patch("main.search_news", return_value=[article]),
            patch("main.read_article", return_value="This article discusses global events."),
            patch("main.summarize_article", return_value=None),
            patch("main.save_article"),
            redirect_stdout(output),
        ):
            results = run_agent("global warfare")

        self.assertEqual(results, [])
        self.assertIn("Relevance Score (topic-term coverage): 0.5", output.getvalue())
        self.assertIn("Score threshold met. Summarizing...", output.getvalue())
        self.assertIn("model returned no structured summary", output.getvalue())

    def test_skips_an_article_after_a_summary_error(self):
        article = {
            "title": "Artificial intelligence update",
            "url": "https://example.com/article",
            "source": "Example",
            "published": "Today",
        }
        output = io.StringIO()
        with (
            patch("main.search_news", return_value=[article]),
            patch("main.read_article", return_value="This article discusses AI."),
            patch(
                "main.summarize_article",
                side_effect=SummarizationError("The model truncated its response."),
            ),
            patch("main.save_article"),
            redirect_stdout(output),
        ):
            results = run_agent("artificial intelligence")

        self.assertEqual(results, [])
        self.assertIn("The model truncated its response", output.getvalue())

    def test_stops_after_a_402_and_keeps_completed_summaries(self):
        articles = [
            {
                "title": "Artificial intelligence update",
                "url": "https://example.com/first",
                "source": "Example",
                "published": "Today",
            },
            {
                "title": "Another artificial intelligence update",
                "url": "https://example.com/second",
                "source": "Example",
                "published": "Today",
            },
        ]
        output = io.StringIO()
        with (
            patch("main.search_news", return_value=articles),
            patch("main.read_article", return_value="This article discusses AI."),
            patch(
                "main.summarize_article",
                side_effect=[
                    _summary(),
                    SummarizationError("In-flight budget exhausted.", status_code=402),
                ],
            ) as summarize,
            patch("main.save_article"),
            redirect_stdout(output),
        ):
            results = run_agent("artificial intelligence")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["summary"], "Completed summary.")
        self.assertEqual(summarize.call_count, 2)
        self.assertIn("Stopping summary generation", output.getvalue())

    def test_saves_structured_results_and_can_read_them_back(self):
        article = {
            "title": "Artificial intelligence update",
            "url": "https://example.com/article",
            "source": "Example",
            "published": "Today",
        }
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "news.db"
            with (
                patch("main.search_news", return_value=[article]),
                patch("main.read_article", return_value="This article discusses AI."),
                patch("main.summarize_article", return_value=_summary()),
                redirect_stdout(io.StringIO()),
            ):
                results = run_agent(
                    "artificial intelligence",
                    db_path=db_path,
                )

            saved_articles = list_articles(db_path=db_path)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(saved_articles), 1)
        self.assertEqual(saved_articles[0]["url"], article["url"])
        self.assertEqual(saved_articles[0]["summary"], "Completed summary.")
        self.assertEqual(saved_articles[0]["key_points"], ["An important point."])


if __name__ == "__main__":
    unittest.main()
