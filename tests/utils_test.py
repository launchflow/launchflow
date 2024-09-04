import logging
import os
import sys
import unittest
import unittest.mock as mock

from launchflow.utils import logging_output, redirect_stdout_stderr


class TestUtils(unittest.TestCase):
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
