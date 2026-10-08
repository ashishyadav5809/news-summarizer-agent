import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai import APIStatusError

from tools.summarizer import (
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    SummarizationError,
    _create_client,
    model as configured_model,
    summarize_article,
)


def _response(content, finish_reason="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )


def _structured_summary():
    return json.dumps({
        "headline": "A concise headline",
        "summary": "A concise summary.",
        "key_points": ["An important point."],
        "key_takeaway": "The main takeaway.",
    })


class SummarizeArticleTests(unittest.TestCase):
    @patch("tools.summarizer.client.chat.completions.create")
    def test_requests_json_summary_without_an_article_output_section(self, create):
        create.return_value = _response(_structured_summary())

        result = summarize_article("Article body", "Headline", "Source", "Today")

        self.assertEqual(
            result,
            {
                "headline": "A concise headline",
                "summary": "A concise summary.",
                "key_points": ["An important point."],
                "key_takeaway": "The main takeaway.",
                "source": "Source",
                "published": "Today",
            },
        )
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("do not quote or reproduce the article", prompt)
        self.assertIn("valid JSON object", prompt)
        self.assertNotIn("\nArticle:\n", prompt)
        self.assertEqual(create.call_args.kwargs["max_tokens"], 1400)
        self.assertEqual(create.call_args.kwargs["model"], configured_model)

    @patch("tools.summarizer.client.chat.completions.create")
    def test_retries_a_truncated_completion_with_shorter_instructions(self, create):
        create.side_effect = [
            _response("Incomplete", finish_reason="length"),
            _response(_structured_summary()),
        ]

        self.assertEqual(summarize_article("Article body")["summary"], "A concise summary.")
        self.assertEqual(create.call_count, 2)
        retry_prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("<2 concise sentences>", retry_prompt)

    @patch("tools.summarizer.client.chat.completions.create")
    def test_raises_when_model_returns_no_summary(self, create):
        create.return_value = _response(None)

        with self.assertRaisesRegex(RuntimeError, "empty summary"):
            summarize_article("Article body")

    @patch("tools.summarizer.client.chat.completions.create")
    def test_rejects_invalid_structured_output(self, create):
        create.return_value = _response('{"headline": "Missing required fields"}')

        with self.assertRaisesRegex(RuntimeError, "invalid structured JSON"):
            summarize_article("Article body")

    @patch("tools.summarizer.client.chat.completions.create")
    def test_converts_openrouter_402_to_actionable_error(self, create):
        response = httpx.Response(
            402,
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
        )
        create.side_effect = APIStatusError(
            "Insufficient in-flight budget",
            response=response,
            body={
                "error": {
                    "code": "in_flight_budget_exhausted",
                    "metadata": {"headers": {"Retry-After": "120"}},
                }
            },
        )

        with self.assertRaises(SummarizationError) as caught:
            summarize_article("Article body")

        self.assertEqual(caught.exception.status_code, 402)
        self.assertIn("120 seconds", str(caught.exception))
        self.assertIn("openrouter.ai/settings/credits", str(caught.exception))

    @patch("tools.summarizer.OpenAI")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}, clear=True)
    def test_configures_gemini_endpoint_and_model(self, openai):
        _, selected_model = _create_client()

        openai.assert_called_once_with(
            api_key="test-gemini-key",
            base_url=GEMINI_BASE_URL,
        )
        self.assertEqual(selected_model, "gemini-3.8-flash")
        self.assertEqual(selected_model, GEMINI_MODEL)

    @patch("tools.summarizer.OpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "AIza-test-gemini-key"}, clear=True)
    def test_detects_gemini_key_in_legacy_environment_variable(self, openai):
        _, selected_model = _create_client()

        openai.assert_called_once_with(
            api_key="AIza-test-gemini-key",
            base_url=GEMINI_BASE_URL,
        )
        self.assertEqual(selected_model, GEMINI_MODEL)

    @patch("tools.summarizer.OpenAI")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "sk-or-v1-test-key"}, clear=True)
    def test_routes_openrouter_key_stored_in_gemini_variable(self, openai):
        _, selected_model = _create_client()

        openai.assert_called_once_with(
            api_key="sk-or-v1-test-key",
            base_url=OPENROUTER_BASE_URL,
        )
        self.assertEqual(selected_model, OPENROUTER_MODEL)

    @patch("tools.summarizer.OpenAI")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-v1-test-key"}, clear=True)
    def test_uses_openrouter_key_when_both_provider_variables_are_present(self, openai):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "AIza-test-gemini-key"}):
            _, selected_model = _create_client()

        openai.assert_called_once_with(
            api_key="sk-or-v1-test-key",
            base_url=OPENROUTER_BASE_URL,
        )
        self.assertEqual(selected_model, OPENROUTER_MODEL)

    @patch("tools.summarizer.client.chat.completions.create")
    def test_401_error_explains_how_to_configure_the_api_key(self, create):
        response = httpx.Response(
            401,
            request=httpx.Request("POST", "https://example.com/chat/completions"),
        )
        create.side_effect = APIStatusError(
            "Missing Authentication header",
            response=response,
            body={"error": {"message": "Missing Authentication header"}},
        )

        with self.assertRaises(SummarizationError) as caught:
            summarize_article("Article body")

        self.assertEqual(caught.exception.status_code, 401)
        self.assertIn("GEMINI_API_KEY", str(caught.exception))

    @patch("tools.summarizer.client.chat.completions.create")
    @patch("tools.summarizer.model", GEMINI_MODEL)
    def test_404_error_identifies_unavailable_gemini_model(self, create):
        response = httpx.Response(
            404,
            request=httpx.Request("POST", "https://example.com/chat/completions"),
        )
        create.side_effect = APIStatusError(
            "Model is no longer available",
            response=response,
            body=[{"error": {"message": "Model is no longer available"}}],
        )

        with self.assertRaises(SummarizationError) as caught:
            summarize_article("Article body")

        self.assertEqual(caught.exception.status_code, 404)
        self.assertIn("gemini-3.8-flash", str(caught.exception))
        self.assertIn("Check that the model is available", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
