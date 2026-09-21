#!/usr/bin/env python3
"""Exercise a live cache from a runner, using disposable pip/uv environments."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request

ORIGIN = "http://pypi.internal.yesod.work:3141"
INDEX = ORIGIN + "/simple/"
HOST = "pypi.internal.yesod.work"
PACKAGES = ["requests==2.32.5", "numpy==2.3.3", "pydantic==2.11.9"]


def fetch(url, accept=None):
    headers = {"Accept": accept} if accept else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
        return response.read(), response.headers.get("X-PyPI-Cache")


def main():
    html, _ = fetch(INDEX + "requests/", "text/html")
    raw, _ = fetch(INDEX + "requests/", "application/vnd.pypi.simple.v1+json")
    for content in (html, raw):
        assert b"https://files.pythonhosted.org/packages/" not in content
        assert (ORIGIN + "/packages/").encode() in content
    metadata = json.loads(raw)
    wheel = next(f for f in metadata["files"] if f["filename"] == "requests-2.32.5-py3-none-any.whl")
    statuses = []
    for _ in range(2):
        body, status = fetch(wheel["url"])
        assert hashlib.sha256(body).hexdigest() == wheel["hashes"]["sha256"]
        statuses.append(status)
    assert statuses[-1] == "HIT", statuses
    print(json.dumps({"index_formats": ["HTML", "PEP691 JSON"], "wheel_sha256": "verified",
                      "wheel_cache": statuses}), flush=True)

    uv = shutil.which("uv")
    assert uv, "uv must be installed on the client"
    # Prevent ambient runner configuration from changing this isolated test.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("UV_", "PIP_")) and k != "VIRTUAL_ENV"}
    env.update(UV_NO_CONFIG="1", UV_PYTHON_DOWNLOADS="never", PIP_CONFIG_FILE=os.devnull,
               PIP_DISABLE_PIP_VERSION_CHECK="1")
    with tempfile.TemporaryDirectory(prefix="pypi-cache-check-") as work:
        def run(args):
            start = time.monotonic()
            subprocess.run(args, cwd=work, env=env, check=True)
            return round(time.monotonic() - start, 3)

        for client in ("uv", "pip"):
            for attempt in (1, 2):
                venv = Path(work) / f"{client}-{attempt}"
                run([uv, "venv", "--python", "/usr/bin/python3", "--no-cache", str(venv)])
                python = str(venv / "bin/python")
                options = ["--default-index", INDEX, "--allow-insecure-host", HOST]
                if client == "uv":
                    args = [uv, "pip", "install", "--python", python, "--no-cache", *options, *PACKAGES]
                else:
                    run([uv, "pip", "install", "--python", python, "--no-cache", *options, "pip==25.2"])
                    args = [python, "-m", "pip", "install", "--no-cache-dir", "--index-url", INDEX,
                            "--trusted-host", HOST, *PACKAGES]
                seconds = run(args)
                run([python, "-c", "import requests, numpy, pydantic; print(requests.__version__, numpy.__version__, pydantic.__version__)"])
                print(json.dumps({"client": client, "attempt": attempt, "seconds": seconds,
                                  "client_cache": "disabled", "packages": PACKAGES}), flush=True)


if __name__ == "__main__":
    main()
