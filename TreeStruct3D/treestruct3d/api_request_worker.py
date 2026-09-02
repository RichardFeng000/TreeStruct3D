#!/usr/bin/env python3
"""Execute one isolated TreeStruct3D HTTP request over a JSON stdio envelope."""

from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate_3d  # noqa: E402


def main() -> None:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    encoded = payload.get("data_base64")
    data = base64.b64decode(encoded) if encoded is not None else None
    request = urllib.request.Request(
        payload["url"],
        data=data,
        headers=payload.get("headers") or {},
        method=payload.get("method"),
    )
    try:
        value = generate_3d._request_json_direct(
            request,
            timeout=payload.get("socket_timeout"),
            ambiguous_on_disconnect=bool(payload.get("ambiguous_on_disconnect")),
        )
        envelope = {"ok": True, "value": value}
    except BaseException as exc:
        envelope = {
            "ok": False,
            "exception": type(exc).__name__,
            "message": str(exc),
        }
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False))


if __name__ == "__main__":
    main()
