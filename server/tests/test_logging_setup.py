import io
import json
import logging

import pytest

from app.logging_setup import UVICORN_LOGGERS, JsonFormatter, redact, setup_logging


@pytest.fixture
def restore_logging():
    names = ("",) + UVICORN_LOGGERS
    saved = [
        (n, logging.getLogger(n).handlers[:], logging.getLogger(n).propagate,
         logging.getLogger(n).level)
        for n in names
    ]
    yield
    for name, handlers, propagate, level in saved:
        lg = logging.getLogger(name)
        lg.handlers, lg.propagate = handlers, propagate
        lg.setLevel(level)


def test_uvicorn_loggers_use_the_json_formatter(restore_logging):
    setup_logging()
    for name in UVICORN_LOGGERS:
        handlers = logging.getLogger(name).handlers
        assert len(handlers) == 1
        assert isinstance(handlers[0].formatter, JsonFormatter)
        assert logging.getLogger(name).propagate is False


def test_uvicorn_error_output_is_json(restore_logging):
    setup_logging()
    stream = io.StringIO()
    logging.getLogger("uvicorn.error").handlers[0].setStream(stream)
    logging.getLogger("uvicorn.error").error("boom", extra={"ctx": {"token": "abc", "n": 1}})
    line = json.loads(stream.getvalue())
    assert line["logger"] == "uvicorn.error"
    assert line["ctx"] == {"token": "[redacted]", "n": 1}


def test_redact_is_recursive_and_case_insensitive():
    out = redact({"Authorization": "Bearer x", "a": [{"OTP": "1", "k": 2}]})
    assert out == {"Authorization": "[redacted]", "a": [{"OTP": "[redacted]", "k": 2}]}