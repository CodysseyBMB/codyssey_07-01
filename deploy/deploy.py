"""Root-owned deployment entrypoint; never install updates through the deploy key."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path("/opt/codyssey-aichat")
MAX_UPLOAD = 512 * 1024 * 1024


def validate_revision(revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full lowercase commit SHA")


def validate_archive(path, revision):
    validate_revision(revision)
    with tarfile.open(path, "r:gz") as archive:
        manifests = [item for item in archive if item.name == "manifest.json"]
        if len(manifests) != 1 or not manifests[0].isfile() or manifests[0].size > 65536:
            raise ValueError("Expected one bounded Docker manifest")
        manifest = json.load(archive.extractfile(manifests[0]))
        if len(manifest) != 1 or manifest[0].get("RepoTags") != [f"codyssey-aichat:{revision}"]:
            raise ValueError("Only the requested codyssey-aichat image is permitted")
        legacy = [item for item in archive.getmembers() if item.name == "repositories"]
        if len(legacy) > 1:
            raise ValueError("Duplicate repositories metadata")
        if legacy:
            if not legacy[0].isfile() or legacy[0].size > 65536:
                raise ValueError("Invalid repositories metadata")
            repositories = json.load(archive.extractfile(legacy[0]))
            if list(repositories) != ["codyssey-aichat"] or list(repositories["codyssey-aichat"]) != [revision]:
                raise ValueError("Unexpected legacy image tags")


def receive_archive(stream, path):
    total = 0
    with path.open("wb") as output:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD:
                raise ValueError("Image upload exceeds 512 MiB")
            output.write(chunk)


def start_image(image):
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/root", "APP_IMAGE": image}
    subprocess.run(
        ["docker", "compose", "-f", str(ROOT / "compose.yaml"),
         "up", "-d", "--wait", "--wait-timeout", "90"],
        env=environment, check=True, timeout=120,
    )


def main():
    import fcntl
    import signal

    signal.alarm(600)
    revision = sys.argv[1] if len(sys.argv) == 2 else ""
    validate_revision(revision)
    with (ROOT / "deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix="codyssey-deploy-") as directory:
            path = Path(directory) / "image.tar.gz"
            receive_archive(sys.stdin.buffer, path)
            validate_archive(path, revision)
            subprocess.run(["docker", "load", "--input", str(path)], check=True, timeout=180)
        image = f"codyssey-aichat:{revision}"
        current = ROOT / "current-image"
        previous = current.read_text().strip() if current.exists() else None
        try:
            start_image(image)
        except (subprocess.SubprocessError, OSError):
            if previous:
                start_image(previous)
            raise
        current.write_text(image + "\n")
        print(f"Deployed {image}")


if __name__ == "__main__":
    main()
