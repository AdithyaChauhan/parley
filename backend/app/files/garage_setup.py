"""Gets a fresh Garage ready, once (D38): gives the node its role, then makes the
bucket and the app's key. Safe to run again, since each step checks first.

Only this file knows it's Garage: it runs at setup, and the app itself talks
plain S3. With another store, this step is simply not used.

    python -m app.files.garage_setup
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

from app.config import settings

ADMIN_URL = os.environ.get("STORAGE_ADMIN_URL", "http://127.0.0.1:3903")
ADMIN_TOKEN = os.environ.get("STORAGE_ADMIN_TOKEN", "")
# The most the store may hold, so uploads can never fill the disk that the
# database also lives on.
QUOTA_BYTES = int(os.environ.get("STORAGE_QUOTA_BYTES", 5 * 1024**3))
# Garage needs a node size to place data. One node, so it doesn't limit anything.
CAPACITY_BYTES = 5 * 1000**3


def admin(path: str, body: dict | None = None):
    request = urllib.request.Request(
        f"{ADMIN_URL}{path}",
        method="GET" if body is None else "POST",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as reply:
        text = reply.read()
    return json.loads(text) if text else None


def wait_for_garage() -> dict:
    """Its status, as soon as it answers (up to a minute)."""
    for _ in range(60):
        try:
            return admin("/v2/GetClusterStatus")
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)
    sys.exit("Garage didn't answer within a minute")


def ensure_layout(status: dict) -> None:
    node = status["nodes"][0]
    if node.get("role"):
        return
    admin(
        "/v2/UpdateClusterLayout",
        {"roles": [{"id": node["id"], "zone": "local", "capacity": CAPACITY_BYTES, "tags": []}]},
    )
    admin("/v2/ApplyClusterLayout", {"version": status["layoutVersion"] + 1})
    print("Layout applied")


def ensure_key(access_key: str, secret_key: str) -> None:
    try:
        admin("/v2/ImportKey", {"accessKeyId": access_key, "secretAccessKey": secret_key, "name": "parley"})
        print("Key imported")
    except urllib.error.HTTPError as error:
        if error.code != 409:  # 409: it's already there
            raise


def ensure_bucket(name: str, access_key: str) -> None:
    try:
        bucket = admin(f"/v2/GetBucketInfo?globalAlias={name}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        bucket = admin("/v2/CreateBucket", {"globalAlias": name})
        print(f"Bucket {name} created")
    admin(
        "/v2/AllowBucketKey",
        {
            "bucketId": bucket["id"],
            "accessKeyId": access_key,
            "permissions": {"read": True, "write": True, "owner": False},
        },
    )
    admin(f"/v2/UpdateBucket?id={bucket['id']}", {"quotas": {"maxSize": QUOTA_BYTES, "maxObjects": None}})


def main() -> None:
    status = wait_for_garage()
    ensure_layout(status)
    ensure_key(settings.storage_access_key, settings.storage_secret_key)
    ensure_bucket(settings.storage_bucket, settings.storage_access_key)
    # Only on the laptop and in CI, for the tests.
    test_bucket = os.environ.get("TEST_STORAGE_BUCKET")
    if test_bucket:
        ensure_bucket(test_bucket, settings.storage_access_key)
    print("Storage is ready")


if __name__ == "__main__":
    main()
