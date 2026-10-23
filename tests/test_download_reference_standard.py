import importlib.util
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "data" / "download_reference_standard.py"

spec = importlib.util.spec_from_file_location("download_reference_standard", SCRIPT)
drs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drs)

GOOD_CSV = b"\xef\xbb\xbfgc_orgID,name\n1,a\n2,b\n3,c\n4,d\n5,e\n"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self.body


def fake_urlopen(outcomes: list):
    """Return a urlopen that raises or returns each outcome in turn."""
    calls = []

    def urlopen(url, timeout):
        calls.append(url)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeResponse(outcome)

    urlopen.calls = calls
    return urlopen


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(drs.time, "sleep", lambda s: None)


def http_error(code: int) -> HTTPError:
    return HTTPError("https://example.ca", code, "error", None, None)


@pytest.mark.parametrize(
    "transient",
    [
        TimeoutError("The read operation timed out"),
        URLError("connection refused"),
        ConnectionResetError(),
        IncompleteRead(b"partial"),
        http_error(503),
    ],
)
def test_transient_failure_is_retried(monkeypatch, transient):
    urlopen = fake_urlopen([transient, GOOD_CSV])
    monkeypatch.setattr(drs, "urlopen", urlopen)
    assert drs.fetch_with_retry("https://example.ca") == GOOD_CSV
    assert len(urlopen.calls) == 2


def test_read_timeout_on_every_attempt_raises_download_error(monkeypatch):
    urlopen = fake_urlopen([TimeoutError("timed out")] * drs.MAX_ATTEMPTS)
    monkeypatch.setattr(drs, "urlopen", urlopen)
    with pytest.raises(drs.DownloadError, match="unreachable after 3 attempts"):
        drs.fetch_with_retry("https://example.ca")
    assert len(urlopen.calls) == drs.MAX_ATTEMPTS


def test_client_error_is_not_retried(monkeypatch):
    urlopen = fake_urlopen([http_error(404)])
    monkeypatch.setattr(drs, "urlopen", urlopen)
    with pytest.raises(drs.DownloadError, match="HTTP 404"):
        drs.fetch_with_retry("https://example.ca")
    assert len(urlopen.calls) == 1


def test_server_error_on_every_attempt_raises_download_error(monkeypatch):
    urlopen = fake_urlopen([http_error(503)] * drs.MAX_ATTEMPTS)
    monkeypatch.setattr(drs, "urlopen", urlopen)
    with pytest.raises(drs.DownloadError, match="HTTP 503"):
        drs.fetch_with_retry("https://example.ca")
    assert len(urlopen.calls) == drs.MAX_ATTEMPTS


def test_valid_payload_passes(tmp_path):
    drs.validate(GOOD_CSV, tmp_path / "new.csv", {"gc_orgID"})


def test_missing_column_fails(tmp_path):
    with pytest.raises(drs.DownloadError, match="missing columns"):
        drs.validate(GOOD_CSV, tmp_path / "new.csv", {"gc_orgID", "legal_title"})


def test_html_error_page_fails(tmp_path):
    html = b"<!DOCTYPE html><html><body>Service unavailable</body></html>"
    with pytest.raises(drs.DownloadError, match="missing columns"):
        drs.validate(html, tmp_path / "new.csv", {"gc_orgID"})


def test_non_utf8_payload_fails(tmp_path):
    with pytest.raises(drs.DownloadError, match="not a readable CSV"):
        drs.validate(b"\xff\xfe\x00garbage", tmp_path / "new.csv", {"gc_orgID"})


def test_large_shrink_fails(tmp_path):
    current = tmp_path / "current.csv"
    current.write_bytes(GOOD_CSV)
    truncated = b"gc_orgID,name\n1,a\n2,b\n"
    with pytest.raises(drs.DownloadError, match="shrank from 5 to 2 rows"):
        drs.validate(truncated, current, {"gc_orgID"})


def test_small_shrink_passes(tmp_path):
    current = tmp_path / "current.csv"
    current.write_bytes(GOOD_CSV)
    one_org_dropped = b"gc_orgID,name\n1,a\n2,b\n3,c\n4,d\n"
    drs.validate(one_org_dropped, current, {"gc_orgID"})


def test_failed_second_resource_writes_nothing(monkeypatch, tmp_path):
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    first.write_bytes(b"old first")
    monkeypatch.setattr(
        drs,
        "RESOURCES",
        [("https://a.ca", first, {"gc_orgID"}), ("https://b.ca", second, set())],
    )
    urlopen = fake_urlopen([GOOD_CSV] + [TimeoutError()] * drs.MAX_ATTEMPTS)
    monkeypatch.setattr(drs, "urlopen", urlopen)
    assert drs.main() == 1
    assert first.read_bytes() == b"old first"
    assert not second.exists()


def test_success_writes_every_resource(monkeypatch, tmp_path):
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    monkeypatch.setattr(
        drs,
        "RESOURCES",
        [("https://a.ca", first, {"gc_orgID"}), ("https://b.ca", second, set())],
    )
    monkeypatch.setattr(drs, "urlopen", fake_urlopen([GOOD_CSV, GOOD_CSV]))
    assert drs.main() == 0
    assert first.read_bytes() == GOOD_CSV
    assert second.read_bytes() == GOOD_CSV
