"""Offline translation integration tests: no database writes or paid API calls."""

import json
import unittest
from unittest.mock import Mock, patch

from flask import Flask

from src.routes.note import note_bp
import translator


class TranslationTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(note_bp, url_prefix="/api")
        self.client = app.test_client()
        self.draft = {"title": "Greeting", "content": "How are you?",
                      "target_language": "Simplified Chinese"}

    def response(self, output):
        response = Mock(ok=True)
        response.json.return_value = {"choices": [{"message": {"content": output}}]}
        return response

    def test_json_translation_and_prompt(self):
        reply = self.response(json.dumps({"title": "问候", "content": "你好吗？"}))
        with patch("translator.load_dotenv"), \
                patch.dict("os.environ", {"open_router_key": "test-placeholder"}), \
                patch("translator.requests.post", return_value=reply) as post:
            response = self.client.post("/api/notes/translate", json=self.draft)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"title": "问候", "content": "你好吗？",
                                        "target_language": "Simplified Chinese"})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(json.loads(payload["messages"][1]["content"]),
                         {"title": "Greeting", "content": "How are you?"})
        self.assertEqual(payload["messages"][0]["content"],
                         translator.PROMPT_PATH.read_text().replace(
                             "{target_language}", "Simplified Chinese"))
        self.assertEqual(payload["response_format"]["type"], "json_schema")

    def test_invalid_inputs_do_not_call_model(self):
        invalid = [None, [], {}, {"title": 123}, {"content": ["text"]},
                   {"content": "Hello", "target_language": "unsupported"},
                   {"content": "Hello", "target_language": []},
                   {"title": "x" * 201}, {"content": "x" * 20001}]
        with patch("translator.requests.post") as post:
            for data in invalid:
                with self.subTest(data_type=type(data).__name__):
                    response = self.client.post("/api/notes/translate", json=data)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("error", response.json)
            post.assert_not_called()

    def test_bad_model_output_is_json_error(self):
        outputs = ["not JSON", "[]", '{}', '{"title": 1, "content": "Hi"}',
                   '{"title": "Hi", "content": ""}',
                   '{"title": "Hi", "content": "Hi", "extra": 1}']
        for output in outputs:
            with self.subTest(output=output), \
                    patch("translator._request_completion", return_value=output):
                response = self.client.post("/api/notes/translate", json=self.draft)
                self.assertEqual(response.status_code, 502)
                self.assertIn("error", response.json)

    def test_missing_key_and_network_failure(self):
        with patch("translator.load_dotenv"), patch.dict("os.environ", {}, clear=True):
            response = self.client.post("/api/notes/translate", json=self.draft)
            self.assertEqual(response.status_code, 502)
        for error in [translator.requests.Timeout(), translator.requests.ConnectionError()]:
            with patch("translator.load_dotenv"), \
                    patch.dict("os.environ", {"open_router_key": "test-placeholder"}), \
                    patch("translator.requests.post", side_effect=error):
                response = self.client.post("/api/notes/translate", json=self.draft)
                self.assertEqual(response.status_code, 502)
                self.assertIn("error", response.json)

    def test_cli_translation_still_returns_text(self):
        with patch("translator._request_completion", return_value="你好吗？"):
            self.assertEqual(translator.llm_generate("How are you?"), "你好吗？")


if __name__ == "__main__":
    unittest.main()
