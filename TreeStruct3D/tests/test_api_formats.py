import http.client
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from run_stage7 import (
    AmbiguousRemoteResultError,
    API_FORMAT_GEMINI_GENERATE_CONTENT,
    API_FORMAT_LMSTUDIO,
    API_FORMAT_OPENAI_CHAT,
    API_FORMAT_OPENAI_RESPONSES,
    BackgroundResponseError,
    background_state_path,
    build_api_payload,
    call_code,
    call_configured_model_api,
    call_model_api,
    extract_message,
    extract_reasoning,
    gemini_user_parts,
    normalize_api_timeout,
    safe_to_retry_api_error,
)


class ApiFormatTest(unittest.TestCase):
    @staticmethod
    def json_http_response(value):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(value).encode("utf-8")
        return response

    def test_native_gemini_generate_content_payload(self):
        payload = build_api_payload(
            api_format=API_FORMAT_GEMINI_GENERATE_CONTENT,
            model="gemini-3.1-pro-preview",
            system_prompt="system",
            user_prompt="make a fish",
            max_output_tokens=32768,
            reasoning_effort="high",
        )
        self.assertEqual(
            payload,
            {
                "system_instruction": {"parts": [{"text": "system"}]},
                "contents": [
                    {"role": "user", "parts": [{"text": "make a fish"}]}
                ],
                "generationConfig": {
                    "maxOutputTokens": 32768,
                    "thinkingConfig": {"thinkingLevel": "high"},
                },
            },
        )

    def test_native_gemini_image_part(self):
        self.assertEqual(
            gemini_user_parts(
                [{"type": "image", "mime": "image/png", "data": b"png"}]
            ),
            [
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": "cG5n",
                    }
                }
            ],
        )

    def test_native_gemini_message_and_reasoning_are_extracted(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "private summary", "thought": True},
                            {"text": "print('ok')"},
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_message(response), "print('ok')")
        self.assertEqual(extract_reasoning(response), "private summary")

    def test_zero_timeout_means_unlimited_wait(self):
        self.assertIsNone(normalize_api_timeout(0))
        self.assertIsNone(normalize_api_timeout(-1))
        self.assertIsNone(normalize_api_timeout(None))
        self.assertEqual(normalize_api_timeout(600), 600)

    def test_openai_chat_completions_payload_matches_tokenpony_template(self):
        payload = build_api_payload(
            api_format=API_FORMAT_OPENAI_CHAT,
            model="kimi-k3",
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello!",
            max_output_tokens=16384,
            reasoning_effort="high",
        )
        self.assertEqual(payload["model"], "kimi-k3")
        self.assertEqual(
            payload["messages"],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        )
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_tokens"], 16384)
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertNotIn("system_prompt", payload)
        self.assertNotIn("input", payload)

    def test_lmstudio_payload_is_unchanged(self):
        payload = build_api_payload(
            api_format=API_FORMAT_LMSTUDIO,
            model="google/gemma-4-31b",
            system_prompt="system",
            user_prompt="user",
            max_output_tokens=8192,
        )
        self.assertEqual(
            payload,
            {
                "model": "google/gemma-4-31b",
                "system_prompt": "system",
                "input": "user",
                "max_output_tokens": 8192,
            },
        )

    def test_native_openai_responses_payload(self):
        payload = build_api_payload(
            api_format=API_FORMAT_OPENAI_RESPONSES,
            model="gpt-5.5",
            system_prompt="system",
            user_prompt="create Blender Python",
            max_output_tokens=32768,
            reasoning_effort="high",
        )
        self.assertEqual(
            payload,
            {
                "model": "gpt-5.5",
                "instructions": "system",
                "input": "create Blender Python",
                "store": False,
                "max_output_tokens": 32768,
                "reasoning": {"effort": "high"},
            },
        )

    def test_native_openai_background_payload_adds_only_background_flag(self):
        payload = build_api_payload(
            api_format=API_FORMAT_OPENAI_RESPONSES,
            model="gpt-5.5",
            system_prompt="system",
            user_prompt="create Blender Python",
            background=True,
        )
        self.assertTrue(payload["background"])
        self.assertFalse(payload["store"])

    def test_openai_background_persists_id_before_short_get_polling(self):
        queued = {"id": "resp_test", "status": "queued", "output": []}
        completed = {
            "id": "resp_test",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "print('ok')"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "response.background.json"
            calls = []

            def urlopen(request, timeout=None):
                calls.append((request, timeout))
                if request.get_method() == "POST":
                    return self.json_http_response(queued)
                saved = json.loads(state_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["response_id"], "resp_test")
                self.assertEqual(saved["status"], "queued")
                return self.json_http_response(completed)

            with mock.patch("run_stage7._REQUEST_URLOPEN_OVERRIDE", side_effect=urlopen), mock.patch(
                "run_stage7.time.sleep"
            ):
                response = call_model_api(
                    api_url="https://api.openai.com/v1/responses",
                    api_key="test-key",
                    model="gpt-5.5",
                    system_prompt="system",
                    user_prompt="user",
                    timeout=0,
                    api_format=API_FORMAT_OPENAI_RESPONSES,
                    background_state=state_path,
                    background_poll_interval=0.1,
                    background_request_timeout=60,
                )

            self.assertEqual(response["status"], "completed")
            self.assertEqual([item[0].get_method() for item in calls], ["POST", "GET"])
            self.assertEqual([item[1] for item in calls], [60, 60])
            submitted = json.loads(calls[0][0].data.decode("utf-8"))
            self.assertTrue(submitted["background"])
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "completed")
            self.assertEqual(saved["poll_count"], 1)

    def test_openai_background_restart_resumes_without_another_post(self):
        queued = {"id": "resp_resume", "status": "queued", "output": []}
        completed = {
            "id": "resp_resume",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "print('ok')"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            response_path = Path(temporary) / "response.json"
            state_path = background_state_path(response_path)
            first_responses = [
                self.json_http_response(queued),
                self.json_http_response(completed),
            ]
            with mock.patch(
                "run_stage7._REQUEST_URLOPEN_OVERRIDE", side_effect=first_responses
            ), mock.patch("run_stage7.time.sleep"):
                call_model_api(
                    api_url="https://api.openai.com/v1/responses",
                    api_key="test-key",
                    model="gpt-5.5",
                    system_prompt="system",
                    user_prompt="same request",
                    timeout=0,
                    api_format=API_FORMAT_OPENAI_RESPONSES,
                    background_state=state_path,
                )

            with mock.patch(
                "run_stage7._REQUEST_URLOPEN_OVERRIDE",
                return_value=self.json_http_response(completed),
            ) as urlopen:
                resumed = call_model_api(
                    api_url="https://api.openai.com/v1/responses",
                    api_key="test-key",
                    model="gpt-5.5",
                    system_prompt="system",
                    user_prompt="same request",
                    timeout=0,
                    api_format=API_FORMAT_OPENAI_RESPONSES,
                    background_state=state_path,
                )
            self.assertEqual(resumed["status"], "completed")
            request = urlopen.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertTrue(request.full_url.endswith("/responses/resp_resume"))

    def test_openai_background_poll_failure_retries_get_not_post(self):
        queued = {"id": "resp_poll", "status": "queued", "output": []}
        completed = {"id": "resp_poll", "status": "completed", "output": []}
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "response.background.json"
            outcomes = [
                self.json_http_response(queued),
                urllib.error.URLError("temporary poll failure"),
                self.json_http_response(completed),
            ]
            with mock.patch(
                "run_stage7._REQUEST_URLOPEN_OVERRIDE", side_effect=outcomes
            ) as urlopen, mock.patch("run_stage7.time.sleep"):
                response = call_model_api(
                    api_url="https://api.openai.com/v1/responses",
                    api_key="test-key",
                    model="gpt-5.5",
                    system_prompt="system",
                    user_prompt="user",
                    timeout=0,
                    api_format=API_FORMAT_OPENAI_RESPONSES,
                    background_state=state_path,
                )
            self.assertEqual(response["status"], "completed")
            methods = [call.args[0].get_method() for call in urlopen.call_args_list]
            self.assertEqual(methods, ["POST", "GET", "GET"])

    def test_openai_background_failed_status_is_not_resubmitted(self):
        failed = {
            "id": "resp_failed",
            "status": "failed",
            "error": {"code": "server_error", "message": "failed"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "response.background.json"
            with mock.patch(
                "run_stage7._REQUEST_URLOPEN_OVERRIDE",
                return_value=self.json_http_response(failed),
            ) as urlopen:
                with self.assertRaisesRegex(BackgroundResponseError, "status=failed"):
                    call_model_api(
                        api_url="https://api.openai.com/v1/responses",
                        api_key="test-key",
                        model="gpt-5.5",
                        system_prompt="system",
                        user_prompt="user",
                        timeout=0,
                        api_format=API_FORMAT_OPENAI_RESPONSES,
                        background_state=state_path,
                    )
            self.assertEqual(urlopen.call_count, 1)
            self.assertEqual(urlopen.call_args.args[0].get_method(), "POST")

    def test_configured_openai_call_derives_durable_background_sidecar(self):
        config = {
            "api_url": "https://api.openai.com/v1/responses",
            "api_key": "test-key",
            "model": "gpt-5.5",
            "api_format": API_FORMAT_OPENAI_RESPONSES,
            "openai_background": True,
            "openai_poll_interval": 7,
            "openai_request_timeout": 45,
        }
        with tempfile.TemporaryDirectory() as temporary:
            response_path = Path(temporary) / "response_initial.json"
            with mock.patch(
                "run_stage7.call_model_api",
                return_value={"id": "resp_test", "status": "completed"},
            ) as call:
                call_configured_model_api(
                    config,
                    "system",
                    "user",
                    timeout=0,
                    response_path=response_path,
                )
            kwargs = call.call_args.kwargs
            self.assertEqual(
                kwargs["background_state"],
                response_path.with_suffix(".background.json"),
            )
            self.assertEqual(kwargs["background_poll_interval"], 7.0)
            self.assertEqual(kwargs["background_request_timeout"], 45)

    def test_native_openai_responses_message_is_extracted(self):
        response = {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "print('ok')"}
                    ],
                },
            ]
        }
        self.assertEqual(extract_message(response), "print('ok')")

    def test_openai_response_message_and_reasoning_are_extracted(self):
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "reasoning_content": "private planning",
                        "content": "print('ok')",
                    }
                }
            ]
        }
        self.assertEqual(extract_message(response), "print('ok')")
        self.assertEqual(extract_reasoning(response), "private planning")

    def test_remote_disconnect_is_not_retried_after_unknown_billing(self):
        with mock.patch(
            "run_stage7.urllib.request.urlopen",
            side_effect=http.client.RemoteDisconnected("closed"),
        ):
            with self.assertRaisesRegex(
                AmbiguousRemoteResultError,
                "automatic retry disabled",
            ):
                call_model_api(
                    api_url="https://api.openai.com/v1/responses",
                    api_key="test-key",
                    model="gpt-5.5",
                    system_prompt="system",
                    user_prompt="user",
                    timeout=1,
                    api_format=API_FORMAT_OPENAI_RESPONSES,
                )

    def test_call_code_does_not_retry_ambiguous_remote_result(self):
        config = {
            "api_url": "https://api.openai.com/v1/responses",
            "api_key": "test-key",
            "model": "gpt-5.5",
            "api_format": API_FORMAT_OPENAI_RESPONSES,
            "api_retries": 5,
        }
        error = AmbiguousRemoteResultError("unknown billed result")
        with mock.patch("run_stage7.call_model_api", side_effect=error) as call:
            with self.assertRaises(AmbiguousRemoteResultError):
                call_code(config, "system", "user", timeout=1)
        call.assert_called_once()

    def test_retry_safety_requires_an_explicit_http_rejection(self):
        self.assertTrue(safe_to_retry_api_error(RuntimeError("HTTP 503: busy")))
        self.assertTrue(safe_to_retry_api_error(RuntimeError("HTTP 429: quota")))
        self.assertFalse(safe_to_retry_api_error(TimeoutError("timed out")))
        self.assertFalse(
            safe_to_retry_api_error(OSError("connection reset after request"))
        )


if __name__ == "__main__":
    unittest.main()
