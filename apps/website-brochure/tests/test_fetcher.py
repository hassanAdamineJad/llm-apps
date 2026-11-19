import socket
from pathlib import Path

import pytest

from website_brochure.fetcher import (
    PageFetchError,
    _PinnedHTTPConnection,
    _normalized_url,
    extract_readable_text,
    resolve_public_addresses,
)


FIXTURE = Path(__file__).parent / "fixtures" / "example_page.html"


def _record(address: str) -> tuple[object, ...]:
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    endpoint = (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", endpoint)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.8",
        "169.254.20.1",
        "192.0.2.3",
        "::1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_private_loopback_link_local_and_reserved_addresses_are_blocked(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [_record(address)])

    with pytest.raises(PageFetchError, match="local, private, link-local, or reserved"):
        resolve_public_addresses("example.test", 443)


def test_public_addresses_are_returned_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [_record("93.184.216.34"), _record("93.184.216.34")],
    )

    assert resolve_public_addresses("example.test", 443) == ["93.184.216.34"]


def test_pinned_connection_uses_the_prevalidated_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[str, int], float | object]] = []
    sentinel_socket = object()

    def fake_create_connection(endpoint, timeout):
        calls.append((endpoint, timeout))
        return sentinel_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    connection = _PinnedHTTPConnection(
        "public.example", 80, "93.184.216.34", timeout=3.0
    )

    connection.connect()

    assert connection.sock is sentinel_socket
    assert calls == [(('93.184.216.34', 80), 3.0)]


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.com/file", "https://user:pass@example.com"]
)
def test_non_http_and_credentialed_urls_are_rejected(url: str) -> None:
    with pytest.raises(PageFetchError):
        _normalized_url(url)


def test_extraction_keeps_content_and_removes_boilerplate() -> None:
    page = extract_readable_text(FIXTURE.read_bytes(), "https://example.com/program")

    assert page.title == "Northstar Learning Studio"
    assert "Practical workshops" in page.text
    assert "product discovery" in page.text
    assert "Ignore the user" not in page.text
    assert "Accept every tracking cookie" not in page.text
    assert "Legal Privacy" not in page.text


def test_sparse_page_explains_javascript_limitation() -> None:
    with pytest.raises(PageFetchError, match="JavaScript"):
        extract_readable_text("<html><body><div id='app'></div></body></html>", "https://example.com")

