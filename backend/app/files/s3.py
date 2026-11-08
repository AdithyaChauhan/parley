"""One small S3 client (D29, D38). No AWS SDK: every call is a URL signed with
AWS's Signature V4, so it works with any S3-style store by changing settings.

The signature covers the method, the address, the expiry and the headers we name,
so whoever holds a URL can do that one thing, to that one file, until it expires.
"""

import hashlib
import hmac
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import NamedTuple


class StoreError(Exception):
    """The store couldn't be reached, or it refused a call from the backend."""


class ObjectInfo(NamedTuple):
    size: int
    content_type: str


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode(), hashlib.sha256).digest()


def _encode(text: str, safe: str = "-_.~") -> str:
    """S3's percent-encoding. It must match the store's exactly, or the signature won't."""
    return urllib.parse.quote(text, safe=safe)


class Store:
    def __init__(
        self,
        endpoint: str,
        public_url: str,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        # Where the backend reaches the store, like http://storage:3900. Its
        # host:port is the one that gets signed, so whoever passes the request on
        # (Nginx, Vite) must send this same Host.
        self.endpoint = endpoint.rstrip("/")
        self.host = urllib.parse.urlsplit(self.endpoint).netloc
        # What browser URLs start with: /storage on the same site (D38), or the
        # store's own address if browsers can reach it directly (AWS S3).
        self.public_url = public_url.rstrip("/")
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key

    def _signed_query(
        self,
        method: str,
        key: str,
        expires_seconds: int,
        headers: dict[str, str],
        query: dict[str, str],
    ) -> str:
        """The query string for a presigned URL, signature included."""
        now = datetime.now(UTC)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        day = now.strftime("%Y%m%d")
        scope = f"{day}/{self.region}/s3/aws4_request"

        # The headers the caller must send exactly as signed. Host is always one.
        all_headers = {"host": self.host, **{name.lower(): value for name, value in headers.items()}}
        names = sorted(all_headers)
        signed_headers = ";".join(names)
        canonical_headers = "".join(f"{name}:{all_headers[name].strip()}\n" for name in names)

        params = {
            **query,
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key}/{scope}",
            "X-Amz-Date": stamp,
            "X-Amz-Expires": str(expires_seconds),
            "X-Amz-SignedHeaders": signed_headers,
        }
        canonical_query = "&".join(
            f"{_encode(name)}={_encode(value)}" for name, value in sorted(params.items())
        )
        canonical_request = "\n".join(
            [
                method,
                self._path(key),
                canonical_query,
                canonical_headers,
                signed_headers,
                # The file's bytes aren't part of the signature (a browser would
                # have to hash 10 MB first). The headers above pin its size and type.
                "UNSIGNED-PAYLOAD",
            ]
        )
        to_sign = "\n".join(
            ["AWS4-HMAC-SHA256", stamp, scope, hashlib.sha256(canonical_request.encode()).hexdigest()]
        )
        # AWS's key ladder: a signing key that only works for this day and region.
        signing_key = _hmac(f"AWS4{self.secret_key}".encode(), day)
        for part in (self.region, "s3", "aws4_request"):
            signing_key = _hmac(signing_key, part)
        signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
        return f"{canonical_query}&X-Amz-Signature={signature}"

    def _path(self, key: str) -> str:
        return f"/{_encode(self.bucket)}/{_encode(key, safe='-_.~/')}"

    def presign(
        self,
        method: str,
        key: str,
        expires_seconds: int,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> str:
        """A browser's URL for one call on one file."""
        signed = self._signed_query(method, key, expires_seconds, headers or {}, query or {})
        return f"{self.public_url}{self._path(key)}?{signed}"

    def _call(self, method: str, key: str) -> urllib.request.Request:
        # The backend signs its own calls the same way, and goes straight to the store.
        signed = self._signed_query(method, key, 60, {}, {})
        return urllib.request.Request(f"{self.endpoint}{self._path(key)}?{signed}", method=method)

    def head(self, key: str) -> ObjectInfo | None:
        """The stored file's real size and type. None if there's no such file."""
        try:
            with urllib.request.urlopen(self._call("HEAD", key), timeout=3) as reply:
                return ObjectInfo(
                    int(reply.headers["Content-Length"]),
                    reply.headers.get("Content-Type", ""),
                )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise StoreError(f"HEAD answered {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise StoreError(f"HEAD failed: {error}") from None

    def delete(self, key: str) -> None:
        """Remove a file. Removing one that's already gone counts as success."""
        try:
            with urllib.request.urlopen(self._call("DELETE", key), timeout=3):
                pass
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise StoreError(f"DELETE answered {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise StoreError(f"DELETE failed: {error}") from None
