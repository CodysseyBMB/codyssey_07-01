import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "deploy.py"
REVISION = "a" * 40


class DeploymentArchiveTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("deploy", SCRIPT)
        self.deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.deploy)

    def archive(self, path, tags):
        with tarfile.open(path, "w:gz") as archive:
            payload = json.dumps([{"RepoTags": tags}]).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    def test_accepts_only_the_requested_app_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.tar.gz"
            self.archive(path, [f"codyssey-aichat:{REVISION}"])
            self.deploy.validate_archive(path, REVISION)

    def test_rejects_images_that_would_retag_other_services(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.tar.gz"
            self.archive(path, [f"codyssey-aichat:{REVISION}", "nginx:latest"])
            with self.assertRaises(ValueError):
                self.deploy.validate_archive(path, REVISION)

    def test_rejects_non_commit_arguments(self):
        for revision in ["latest", "a" * 39, "a" * 40 + ";id", "../main"]:
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.deploy.validate_revision(revision)

    def test_rejects_duplicate_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.tar.gz"
            self.archive(path, [f"codyssey-aichat:{REVISION}"])
            # A second manifest must not be interpreted differently by Docker.
            with tarfile.open(path, "r:gz") as source:
                payload = source.extractfile("manifest.json").read()
            with tarfile.open(path, "w:gz") as archive:
                for _ in range(2):
                    info = tarfile.TarInfo("manifest.json")
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
            with self.assertRaises(ValueError):
                self.deploy.validate_archive(path, REVISION)
