import copy
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from codex_decisions import core

REQUEST = {"input": "Two isolated modules have explicit owners and synthetic checks.", "questions": [
    {"name": "independent", "type": "predicate", "instructions": "Is the work independently verifiable?"}]}


class Response(io.BytesIO):
    headers = {"x-request-id": "synthetic-request"}


class Transport:
    def __init__(self, data=None, error=None):
        self.data = data or {"model": "gpt-6-luna", "answers": [{"name": "independent", "type": "predicate", "probability": 0.7}],
                             "usage": {"input_tokens": 30, "output_tokens": 0, "total_tokens": 30}}
        self.error = error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return Response(json.dumps(self.data).encode())


class DecisionsTests(unittest.TestCase):
    def test_validation_never_sends_or_echoes_evidence(self):
        result = core.preview(REQUEST)
        self.assertEqual(result["status"], "validated")
        self.assertNotIn(REQUEST["input"], json.dumps(result))

    def test_authority_and_credentials_gate_network(self):
        transport = Transport()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(core.evaluate(REQUEST, core.DEFAULT_CONFIG, opener=transport)["status"], "approval_required")
            self.assertEqual(core.evaluate(REQUEST, core.DEFAULT_CONFIG, approved=True, opener=transport)["status"], "needs_credentials")
        self.assertEqual(transport.calls, [])

    def test_one_request_exact_endpoint_and_no_secret_output(self):
        transport = Transport()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-secret"}):
            result = core.evaluate(REQUEST, core.DEFAULT_CONFIG, approved=True, opener=transport)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(transport.calls), 1)
        req, timeout = transport.calls[0]
        self.assertEqual(req.full_url, "https://api.openai.com/v1/decisions")
        self.assertEqual(req.method, "POST")
        self.assertEqual(json.loads(req.data)["input"], REQUEST["input"])
        self.assertNotIn("synthetic-secret", json.dumps(result))

    def test_explicit_access_token_variable(self):
        config = {**core.DEFAULT_CONFIG, "credential_env": "OPENAI_ACCESS_TOKEN"}
        transport = Transport()
        with patch.dict(os.environ, {"OPENAI_ACCESS_TOKEN": "synthetic-token"}, clear=True):
            self.assertEqual(core.evaluate(REQUEST, config, approved=True, opener=transport)["status"], "ok")
        self.assertEqual(transport.calls[0][0].get_header("Authorization"), "Bearer synthetic-token")

    def test_refusal_is_not_pass(self):
        transport = Transport()
        transport.data["answers"] = [{"name": "independent", "type": "refusal"}]
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic"}):
            self.assertEqual(core.evaluate(REQUEST, core.DEFAULT_CONFIG, approved=True, opener=transport)["status"], "refused")

    def test_failures_never_retry_or_echo_body(self):
        for error in (HTTPError(core.ENDPOINT, 401, "secret body", {}, None), URLError("secret body"), TimeoutError()):
            transport = Transport(error=error)
            with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic"}):
                result = core.evaluate(REQUEST, core.DEFAULT_CONFIG, approved=True, opener=transport)
            self.assertEqual(len(transport.calls), 1)
            self.assertNotIn("secret body", json.dumps(result))
            self.assertNotEqual(result["status"], "ok")

    def test_invalid_request_variants(self):
        invalid = []
        for changes in ({"model": "other"}, {"questions": []}, {"input": ""}, {"input": "x" * (core.MAX_BYTES + 1)}, {"extra": True}):
            invalid.append({**REQUEST, **changes})
        duplicate = copy.deepcopy(REQUEST)
        duplicate["questions"] *= 2
        invalid.append(duplicate)
        invalid.append({**REQUEST, "questions": [{"type": [], "name": "bad", "instructions": "Check"}]})
        invalid.append({**REQUEST, "input": [{"role": [], "content": "text"}]})
        invalid.append({**REQUEST, "input": [{"role": "user", "content": [{"type": "input_image", "image_url": "https://example.com/a.png", "detail": []}]}]})
        for request in invalid:
            with self.subTest(request=str(request)[:100]), self.assertRaises(core.Problem):
                core.validate(request)

    def test_json_and_image_boundaries(self):
        request = copy.deepcopy(REQUEST)
        request["input"] = [{"role": "user", "content": [{"type": "input_json", "data": {"temperature": 22}}]}]
        core.validate(request)
        request["input"][0]["content"] = [{"type": "input_image", "image_url": "file:///secret.png"}]
        with self.assertRaises(core.Problem):
            core.validate(request)
        request["input"][0]["content"] = [{"type": "input_image", "image_url": "data:image/png;base64,YWJj"}]
        with self.assertRaises(core.Problem):
            core.validate(request)

    def test_typed_choices_and_scores(self):
        request = {"input": "approved evidence", "questions": [{"type": "choice", "name": "route", "instructions": "Choose", "choices": [{"value": True}, {"value": "true"}]}]}
        core.validate(request)
        response = {"model": "gpt-6-luna", "usage": {"input_tokens": 1, "output_tokens": 0, "total_tokens": 1},
                    "answers": [{"name": "route", "type": "choice", "choice": True, "confidence": 0.8,
                                 "probabilities": [{"value": True, "probability": 0.8}, {"value": "true", "probability": 0.2}]}]}
        core.validate_response(response, request)
        response["answers"][0]["choice"] = 1
        with self.assertRaises(core.Problem):
            core.validate_response(response, request)
        request["questions"] = [{"type": "score", "name": "fit", "instructions": "Rate", "levels": [{"label": "low"}, {"label": "high"}]}]
        response["answers"] = [{"name": "fit", "type": "score", "score": 0.6, "confidence": 0.6,
                                "probabilities": [{"label": "low", "value": 0, "probability": 0.4}, {"label": "high", "value": 1, "probability": 0.6}]}]
        core.validate_response(response, request)
        response["answers"][0]["score"] = 0.4
        with self.assertRaises(core.Problem):
            core.validate_response(response, request)

    def test_malformed_response_is_distinct(self):
        for answer in ({"name": "wrong", "type": "refusal"}, {"name": "independent", "type": "predicate", "probability": True}):
            transport = Transport()
            transport.data["answers"] = [answer]
            with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic"}):
                self.assertEqual(core.evaluate(REQUEST, core.DEFAULT_CONFIG, approved=True, opener=transport)["status"], "invalid_response")

    def test_redirect_is_rejected(self):
        self.assertIsNone(core.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))


if __name__ == "__main__":
    unittest.main()
