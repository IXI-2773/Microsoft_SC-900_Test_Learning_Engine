from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PUBLISHER_BRANCH_PREFIX = "recovery/publish-exact-history/"
SCHEMA_VERSION = 1
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_MANIFEST_KEYS = {
    "schema_version",
    "repository",
    "target_branch",
    "expected_base",
    "expected_head",
    "bundle_sha256",
}


class PublisherError(RuntimeError):
    """Raised when exact-history publication cannot be proven safe."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublisherError(f"invalid manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise PublisherError("manifest must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise PublisherError(f"unsupported schema_version: {payload.get('schema_version')!r}")
    return payload


def validate_manifest(
    manifest: Mapping[str, Any],
    *,
    repository: str,
    default_branch: str,
    publisher_branch: str,
) -> dict[str, Any]:
    missing = REQUIRED_MANIFEST_KEYS - set(manifest)
    unknown = set(manifest) - REQUIRED_MANIFEST_KEYS
    if missing:
        raise PublisherError(f"manifest missing required keys: {sorted(missing)}")
    if unknown:
        raise PublisherError(f"manifest contains unknown keys: {sorted(unknown)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise PublisherError(f"unsupported schema_version: {manifest['schema_version']!r}")
    if manifest["repository"] != repository:
        raise PublisherError(
            f"manifest repository {manifest['repository']!r} does not match {repository!r}"
        )
    if not publisher_branch.startswith(PUBLISHER_BRANCH_PREFIX):
        raise PublisherError(
            f"publisher branch must start with {PUBLISHER_BRANCH_PREFIX!r}: {publisher_branch!r}"
        )

    target_branch = str(manifest["target_branch"])
    if target_branch.startswith("refs/") or target_branch.startswith("-"):
        raise PublisherError(f"invalid target branch name: {target_branch!r}")
    if target_branch == default_branch:
        raise PublisherError("refusing exact-history publication to the default branch")
    if target_branch.startswith(PUBLISHER_BRANCH_PREFIX):
        raise PublisherError("refusing to publish into the exact-history transport namespace")
    if not _is_valid_branch_name(target_branch):
        raise PublisherError(f"invalid target branch name: {target_branch!r}")

    expected_base = str(manifest["expected_base"])
    expected_head = str(manifest["expected_head"])
    bundle_sha256 = str(manifest["bundle_sha256"])
    if not SHA1_RE.fullmatch(expected_base):
        raise PublisherError("expected_base must be a full lowercase 40-character Git SHA-1")
    if not SHA1_RE.fullmatch(expected_head):
        raise PublisherError("expected_head must be a full lowercase 40-character Git SHA-1")
    if not SHA256_RE.fullmatch(bundle_sha256):
        raise PublisherError("bundle_sha256 must be a lowercase SHA-256 hex digest")
    return dict(manifest)


def verify_bundle_digest(bundle_path: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    try:
        with bundle_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PublisherError(f"cannot read bundle: {exc}") from exc
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise PublisherError(f"bundle SHA-256 mismatch: expected {expected_sha256}, got {actual}")


def publish_bundle(
    bundle_path: Path,
    manifest_path: Path,
    *,
    repo_dir: Path,
    remote: str,
    repository: str,
    default_branch: str,
    publisher_branch: str,
) -> str:
    manifest = validate_manifest(
        load_manifest(manifest_path),
        repository=repository,
        default_branch=default_branch,
        publisher_branch=publisher_branch,
    )
    verify_bundle_digest(bundle_path, str(manifest["bundle_sha256"]))

    target_branch = str(manifest["target_branch"])
    expected_base = str(manifest["expected_base"])
    expected_head = str(manifest["expected_head"])
    remote_ref = "refs/exact-history/remote-target"
    candidate_ref = "refs/exact-history/candidate"

    _delete_local_ref(repo_dir, remote_ref)
    _delete_local_ref(repo_dir, candidate_ref)
    try:
        _git(
            repo_dir,
            "fetch",
            "--no-tags",
            remote,
            f"refs/heads/{target_branch}:{remote_ref}",
        )
        remote_head = _git(repo_dir, "rev-parse", remote_ref)
        if remote_head != expected_base:
            raise PublisherError(
                "remote head changed: "
                f"expected {expected_base} for {target_branch}, got {remote_head}"
            )

        _git(repo_dir, "bundle", "verify", str(bundle_path))
        heads = _git(repo_dir, "bundle", "list-heads", str(bundle_path)).splitlines()
        expected_listing = f"{expected_head} refs/heads/{target_branch}"
        if heads != [expected_listing]:
            raise PublisherError(
                "bundle heads do not exactly match manifest target: "
                f"expected {[expected_listing]!r}, got {heads!r}"
            )

        _git(
            repo_dir,
            "fetch",
            "--no-tags",
            str(bundle_path),
            f"refs/heads/{target_branch}:{candidate_ref}",
        )
        candidate_head = _git(repo_dir, "rev-parse", candidate_ref)
        if candidate_head != expected_head:
            raise PublisherError(
                f"bundle candidate mismatch: expected {expected_head}, got {candidate_head}"
            )
        _git(repo_dir, "cat-file", "-e", f"{expected_head}^{{commit}}")
        _git_expect_success(
            repo_dir,
            "merge-base",
            "--is-ancestor",
            expected_base,
            expected_head,
            error=(
                f"candidate {expected_head} is not a fast-forward descendant "
                f"of remote base {expected_base}"
            ),
        )

        # Intentionally no --force or --force-with-lease. Git itself enforces the
        # final fast-forward update in addition to the ancestry proof above.
        _git(repo_dir, "push", remote, f"{expected_head}:refs/heads/{target_branch}")
        published_head = _remote_head(repo_dir, remote, target_branch)
        if published_head != expected_head:
            raise PublisherError(
                f"post-push verification failed: expected {expected_head}, got {published_head}"
            )
        return published_head
    finally:
        _delete_local_ref(repo_dir, candidate_ref)
        _delete_local_ref(repo_dir, remote_ref)


def _is_valid_branch_name(branch: str) -> bool:
    completed = subprocess.run(
        ["git", "check-ref-format", "--branch", branch],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _delete_local_ref(repo_dir: Path, ref: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_dir), "update-ref", "-d", ref],
        check=False,
        capture_output=True,
        text=True,
    )


def _remote_head(repo_dir: Path, remote: str, target_branch: str) -> str:
    output = _git(repo_dir, "ls-remote", remote, f"refs/heads/{target_branch}")
    fields = output.split()
    if len(fields) != 2 or fields[1] != f"refs/heads/{target_branch}":
        raise PublisherError(f"cannot resolve remote target branch {target_branch!r}")
    return fields[0]


def _git(repo_dir: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise PublisherError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _git_expect_success(repo_dir: Path, *args: str, error: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise PublisherError(error)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify and non-force publish an exact Git history bundle."
    )
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-dir", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--publisher-branch", required=True)
    args = parser.parse_args()
    try:
        head = publish_bundle(
            args.bundle,
            args.manifest,
            repo_dir=args.repo_dir,
            remote=args.remote,
            repository=args.repository,
            default_branch=args.default_branch,
            publisher_branch=args.publisher_branch,
        )
    except PublisherError as exc:
        print(f"EXACT_HISTORY_PUBLISH_FAILED: {exc}")
        return 1
    print(f"EXACT_HISTORY_PUBLISHED_HEAD={head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
