import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.publish_exact_history_bundle import (
    PUBLISHER_BRANCH_PREFIX,
    PublisherError,
    create_thin_bundle,
    decode_base64_transport,
    encode_base64_transport,
    main,
    publish_bundle,
)

REPO = "IXI-2773/Microsoft_SC-900_Test_Learning_Engine"
PUBLISHER_BRANCH = PUBLISHER_BRANCH_PREFIX + "sc900-v8-test"
TARGET = "implementation/sc900-v8-baseline"
DEFAULT_BRANCH = "main"


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_user(repo: Path) -> None:
    _git(repo, "config", "user.name", "publisher-test")
    _git(repo, "config", "user.email", "publisher-test@example.test")


def _commit(repo: Path, name: str, message: str) -> str:
    (repo / name).write_text(message + "\n", encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


class ExactHistoryPublisherTests(unittest.TestCase):
    def _workspace(self, tmp: Path) -> dict[str, Path | str]:
        remote = tmp / "remote.git"
        work = tmp / "work"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True, text=True)
        _init_user(work)
        _git(work, "checkout", "-b", DEFAULT_BRANCH)
        _commit(work, "README", "seed")
        _git(work, "push", "-u", "origin", DEFAULT_BRANCH)
        _git(work, "checkout", "-b", TARGET)
        base = _commit(work, "base.txt", "remote implementation head")
        _git(work, "push", "-u", "origin", TARGET)
        head = _commit(work, "candidate.txt", "exact candidate")
        return {"remote": remote, "work": work, "base": base, "head": head}

    def _create(self, tmp: Path, work: Path, base: str, head: str) -> tuple[Path, Path, dict]:
        bundle = tmp / "candidate.bundle"
        manifest_path = tmp / "manifest.json"
        manifest = create_thin_bundle(
            repo_dir=work,
            bundle_path=bundle,
            manifest_path=manifest_path,
            repository=REPO,
            default_branch=DEFAULT_BRANCH,
            publisher_branch=PUBLISHER_BRANCH,
            target_branch=TARGET,
            expected_base=base,
            expected_head=head,
        )
        return bundle, manifest_path, manifest

    def test_publisher_source_has_no_force_push_path(self):
        source = Path(__file__).resolve().parents[1] / "tools" / "publish_exact_history_bundle.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("force-with-lease", text)
        self.assertNotRegex(text, r'["\']--force')
        self.assertNotRegex(text, r"push .*(--force|force-with-lease)")

    def test_successful_publication_against_local_bare_repository(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            ctx = self._workspace(tmp)
            bundle, manifest_path, manifest = self._create(tmp, ctx["work"], ctx["base"], ctx["head"])
            encoded = tmp / "candidate.b64"
            encode_base64_transport(bundle, encoded)
            restored = tmp / "restored.bundle"
            decode_base64_transport(encoded, restored)
            self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), manifest["bundle_sha256"])
            self.assertEqual(bundle.read_bytes(), restored.read_bytes())
            published = publish_bundle(
                bundle,
                manifest_path,
                repo_dir=ctx["work"],
                remote="origin",
                repository=REPO,
                default_branch=DEFAULT_BRANCH,
                publisher_branch=PUBLISHER_BRANCH,
            )
            self.assertEqual(ctx["head"], published)
            self.assertEqual(ctx["head"], _git(ctx["work"], "ls-remote", "origin", f"refs/heads/{TARGET}").split()[0])
            leftover = _git(ctx["work"], "show-ref")
            self.assertNotIn("refs/exact-history/", leftover)

    def test_rejects_diverged_remote_without_changing_it(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            ctx = self._workspace(tmp)
            bundle, manifest_path, _manifest = self._create(tmp, ctx["work"], ctx["base"], ctx["head"])
            other = tmp / "other"
            subprocess.run(["git", "clone", str(ctx["remote"]), str(other)], check=True, capture_output=True, text=True)
            _init_user(other)
            _git(other, "checkout", TARGET)
            diverged = _commit(other, "diverge.txt", "remote diverged")
            _git(other, "push", "origin", TARGET)
            with self.assertRaises(PublisherError) as error:
                publish_bundle(
                    bundle,
                    manifest_path,
                    repo_dir=ctx["work"],
                    remote="origin",
                    repository=REPO,
                    default_branch=DEFAULT_BRANCH,
                    publisher_branch=PUBLISHER_BRANCH,
                )
            self.assertIn("remote head changed", str(error.exception))
            self.assertEqual(diverged, _git(ctx["work"], "ls-remote", "origin", f"refs/heads/{TARGET}").split()[0])

    def test_rejects_malformed_repository_base_head_and_default_branch_target(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            ctx = self._workspace(tmp)
            with self.assertRaises(PublisherError):
                create_thin_bundle(
                    repo_dir=ctx["work"],
                    bundle_path=tmp / "bad.bundle",
                    manifest_path=tmp / "bad.json",
                    repository="someone/else",
                    default_branch=DEFAULT_BRANCH,
                    publisher_branch=PUBLISHER_BRANCH,
                    target_branch=DEFAULT_BRANCH,
                    expected_base=ctx["base"],
                    expected_head=ctx["head"],
                )
            bundle, manifest_path, manifest = self._create(tmp, ctx["work"], ctx["base"], ctx["head"])
            wrong_repo = json.loads(manifest_path.read_text(encoding="utf-8"))
            wrong_repo["repository"] = "someone/else"
            (tmp / "wrong-repo.json").write_text(json.dumps(wrong_repo), encoding="utf-8")
            with self.assertRaises(PublisherError):
                publish_bundle(
                    bundle,
                    tmp / "wrong-repo.json",
                    repo_dir=ctx["work"],
                    remote="origin",
                    repository=REPO,
                    default_branch=DEFAULT_BRANCH,
                    publisher_branch=PUBLISHER_BRANCH,
                )
            wrong_base = dict(manifest)
            wrong_base["expected_base"] = "0" * 40
            (tmp / "wrong-base.json").write_text(json.dumps(wrong_base), encoding="utf-8")
            with self.assertRaises(PublisherError):
                publish_bundle(
                    bundle,
                    tmp / "wrong-base.json",
                    repo_dir=ctx["work"],
                    remote="origin",
                    repository=REPO,
                    default_branch=DEFAULT_BRANCH,
                    publisher_branch="not-a-publisher-branch",
                )
            code = main(
                [
                    "publish",
                    "--bundle",
                    str(bundle),
                    "--manifest",
                    str(manifest_path),
                    "--repo-dir",
                    str(ctx["work"]),
                    "--remote",
                    "origin",
                    "--repository",
                    "wrong/repo",
                    "--default-branch",
                    DEFAULT_BRANCH,
                    "--publisher-branch",
                    PUBLISHER_BRANCH,
                ]
            )
            self.assertEqual(1, code)
            self.assertEqual(ctx["base"], _git(ctx["work"], "ls-remote", "origin", f"refs/heads/{TARGET}").split()[0])


if __name__ == "__main__":
    unittest.main()
