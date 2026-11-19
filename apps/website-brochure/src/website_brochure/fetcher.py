from __future__ import annotations

import asyncio
import http.client
import ipaddress
import re
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup


MAX_REDIRECTS = 4
MAX_DOWNLOAD_BYTES = 1_000_000
MAX_EXTRACTED_CHARS = 20_000
TOTAL_TIMEOUT_SECONDS = 15.0
SOCKET_TIMEOUT_SECONDS = 8.0
MIN_READABLE_WORDS = 45


class PageFetchError(Exception):
    """An expected page-reading failure whose message is safe for the browser."""


@dataclass(frozen=True, slots=True)
class PageContent:
    source_url: str
    title: str
    text: str


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(
        self, host: str, port: int, connect_ip: str, timeout: float
    ) -> None:
        super().__init__(host, port, timeout=timeout)
        self._connect_ip = connect_ip

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._connect_ip, self.port), self.timeout
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self, host: str, port: int, connect_ip: str, timeout: float
    ) -> None:
        super().__init__(
            host,
            port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
        self._connect_ip = connect_ip

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._connect_ip, self.port), self.timeout
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _normalized_url(raw_url: str) -> tuple[str, SplitResult]:
    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise PageFetchError("Enter a public URL beginning with http:// or https://.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise PageFetchError("The website URL must have a public host and no credentials.")
    try:
        parsed.port
    except ValueError as exc:
        raise PageFetchError("The website URL contains an invalid port.") from exc

    normalized = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, "")
    )
    return normalized, urlsplit(normalized)


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def resolve_public_addresses(hostname: str, port: int) -> list[str]:
    """Resolve a hostname and reject it if any answer is not globally routable."""

    try:
        records = socket.getaddrinfo(
            hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror as exc:
        raise PageFetchError("The website host could not be resolved.") from exc

    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise PageFetchError(
            "The URL resolves to a local, private, link-local, or reserved address."
        )
    return addresses


def _host_header(parsed: SplitResult, port: int) -> str:
    assert parsed.hostname is not None
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    default_port = 443 if parsed.scheme == "https" else 80
    return host if port == default_port else f"{host}:{port}"


def _read_response_bytes(response: http.client.HTTPResponse) -> bytes:
    content_length = response.getheader("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_DOWNLOAD_BYTES:
                raise PageFetchError("The page is too large to read safely.")
        except ValueError:
            pass

    chunks: list[bytes] = []
    downloaded = 0
    while True:
        chunk = response.read(min(65_536, MAX_DOWNLOAD_BYTES - downloaded + 1))
        if not chunk:
            break
        downloaded += len(chunk)
        if downloaded > MAX_DOWNLOAD_BYTES:
            raise PageFetchError("The page is too large to read safely.")
        chunks.append(chunk)
    return b"".join(chunks)


def _fetch_html_sync(raw_url: str) -> tuple[str, bytes, str | None]:
    current_url = raw_url
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS

    for redirect_number in range(MAX_REDIRECTS + 1):
        current_url, parsed = _normalized_url(current_url)
        assert parsed.hostname is not None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = resolve_public_addresses(parsed.hostname, port)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PageFetchError("The website took too long to respond.")
        timeout = min(SOCKET_TIMEOUT_SECONDS, remaining)

        connection_class = (
            _PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection
        )
        connection = connection_class(parsed.hostname, port, addresses[0], timeout)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"

        try:
            connection.request(
                "GET",
                target,
                headers={
                    "Host": _host_header(parsed, port),
                    "User-Agent": "WebsiteBrochure/0.1 (+local application)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                response.read(1)
                if not location:
                    raise PageFetchError("The website returned an invalid redirect.")
                if redirect_number == MAX_REDIRECTS:
                    raise PageFetchError("The website redirected too many times.")
                current_url = urljoin(current_url, location)
                continue

            if response.status < 200 or response.status >= 300:
                raise PageFetchError(
                    f"The website returned HTTP {response.status}; no page was read."
                )

            content_type = response.getheader("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type not in {"text/html", "application/xhtml+xml"}:
                raise PageFetchError("The URL did not return an HTML page.")
            body = _read_response_bytes(response)
            charset = response.headers.get_content_charset()
            return current_url, body, charset
        except (TimeoutError, socket.timeout) as exc:
            raise PageFetchError("The website took too long to respond.") from exc
        except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
            raise PageFetchError("The website could not be reached securely.") from exc
        finally:
            connection.close()

    raise PageFetchError("The website redirected too many times.")


def extract_readable_text(
    html: bytes | str, source_url: str, charset: str | None = None
) -> PageContent:
    if isinstance(html, bytes):
        decoded = html.decode(charset or "utf-8", errors="replace")
    else:
        decoded = html

    soup = BeautifulSoup(decoded, "html.parser")
    title = " ".join(soup.title.stripped_strings) if soup.title else "Untitled page"

    for tag in soup(
        ["script", "style", "noscript", "template", "svg", "nav", "footer", "aside", "form"]
    ):
        tag.decompose()
    for element in soup.find_all(
        attrs={"class": re.compile(r"cookie|consent|banner|modal|popup", re.I)}
    ):
        element.decompose()
    for element in soup.find_all(
        attrs={"id": re.compile(r"cookie|consent|banner|modal|popup", re.I)}
    ):
        element.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    blocks: list[str] = []
    for element in root.find_all(["h1", "h2", "h3", "p", "li", "dt", "dd"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if len(text) >= 3 and (not blocks or text != blocks[-1]):
            blocks.append(text)

    text = "\n".join(blocks)[:MAX_EXTRACTED_CHARS].strip()
    if len(text.split()) < MIN_READABLE_WORDS:
        raise PageFetchError(
            "This page has too little readable text. It may be sparse or rendered "
            "mostly with JavaScript; version 1 can read only HTML from the submitted page."
        )
    return PageContent(source_url=source_url, title=title[:300], text=text)


async def fetch_page(raw_url: str) -> PageContent:
    try:
        final_url, body, charset = await asyncio.wait_for(
            asyncio.to_thread(_fetch_html_sync, raw_url),
            timeout=TOTAL_TIMEOUT_SECONDS + 1,
        )
    except TimeoutError as exc:
        raise PageFetchError("The website took too long to respond.") from exc
    return extract_readable_text(body, final_url, charset)

