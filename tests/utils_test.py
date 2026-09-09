import logging
import os
import sys
import unittest
import unittest.mock as mock

import httpx
from requests import Response

from launchflow.utils import get_failure_text, logging_output, redirect_stdout_stderr


class TestUtils(unittest.TestCase):
    def test_get_failure_text_with_detail(self):
        resp = mock.MagicMock()
        resp.status_code = 400
        resp.json.return_value = {"detail": "Invalid resource name"}
        self.assertEqual(get_failure_text(resp), "(400): Invalid resource name")

    def test_get_failure_text_with_message(self):
        resp = mock.MagicMock()
        resp.status_code = 404
        resp.json.return_value = {"message": "Project not found"}
        self.assertEqual(get_failure_text(resp), "(404): Project not found")

    def test_get_failure_text_with_error(self):
        resp = mock.MagicMock()
        resp.status_code = 401
        resp.json.return_value = {"error": "Unauthorized access"}
        self.assertEqual(get_failure_text(resp), "(401): Unauthorized access")

    def test_get_failure_text_with_fastapi_validation_list(self):
        resp = mock.MagicMock()
        resp.status_code = 422
        resp.json.return_value = {
            "detail": [
                {"loc": ["body", "email"], "msg": "value is not a valid email address"},
                {"loc": ["body", "name"], "msg": "field required"},
            ]
        }
        self.assertEqual(
            get_failure_text(resp),
            "(422): value is not a valid email address, field required",
        )

    def test_get_failure_text_fallback_requests_response(self):
        resp = mock.MagicMock(spec=Response)
        resp.status_code = 502
        resp.json.side_effect = ValueError("No JSON")
        resp.reason = "Bad Gateway"
        self.assertEqual(get_failure_text(resp), "(502): Bad Gateway")

    def test_get_failure_text_fallback_httpx_response(self):
        resp = mock.MagicMock(spec=httpx.Response)
        resp.status_code = 500
        resp.json.side_effect = ValueError("No JSON")
        resp.reason_phrase = "Internal Server Error"
        self.assertEqual(get_failure_text(resp), "(500): Internal Server Error")

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_logging_output_to_file(self, mock_open: mock.Mock):
        with logging_output("test.log") as f:
            f.write("test")
        mock_open.assert_called_once_with("test.log", "a")
        handle = mock_open()
        handle.write.assert_called_once_with("test")

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_logging_output_to_devnull(self, mock_open):
        with logging_output(None, drop_logs=True) as f:
            f.write("test")
        mock_open.assert_called_once_with(os.devnull, "w")
        handle = mock_open()
        handle.write.assert_called_once_with("test")

    @mock.patch("sys.stdout")
    def test_logging_output_to_stdout(self, mock_stdout: mock.Mock):
        with logging_output(None) as f:
            f.write("test")
        mock_stdout.write.assert_called_once_with("test")

    @mock.patch("logging.root.handlers", new_callable=list)
    @mock.patch("sys.stderr")
    @mock.patch("sys.stdout")
    def test_redirect_stdout_stderr(
        self,
        mock_stdout: mock.Mock,
        mock_stderr: mock.Mock,
        mock_log_handlers: mock.Mock,
    ):
        mock_fh = mock.MagicMock()
        with redirect_stdout_stderr(mock_fh):
            print("test")
            sys.stderr.write("error")
            logging.warning("logging warning")

        # Where the \n is printed is an implementation detail of print and logging
        expected_calls = [
            mock.call("test"),
            mock.call("\n"),
            mock.call("error"),
            mock.call("logging warning\n"),
        ]

        mock_fh.write.assert_has_calls(expected_calls, any_order=False)


if __name__ == "__main__":
    unittest.main()
