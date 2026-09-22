"""Execute lineage admission and progress persistence from one PyInstaller executable.

The probe loads bytecode and data files out of the given executable. It does not
import the source checkout's application modules.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import marshal
import os
import sys
import tempfile
import traceback
import types
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.loader.pyimod01_archive import PYZ_ITEM_NSPKG, PYZ_ITEM_PKG, ZlibArchiveReader


def _contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_packaged_files(reader: CArchiveReader, destination: Path) -> int:
    extracted = 0
    for name, entry in reader.toc.items():
        typecode = entry[4]
        if typecode not in {"x", "b"}:
            continue
        relative = Path(str(name).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(reader.extract(name))
        extracted += 1
    return extracted


def _pyz_offset(reader: CArchiveReader, executable: Path) -> str:
    matches = [name for name, entry in reader.toc.items() if entry[4] == "z"]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one PYZ archive, found {matches!r}")
    entry_offset = reader.toc[matches[0]][0]
    return f"{executable}?{reader._start_offset + entry_offset}"


def _isolate_import_path(extract_root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script_dir = Path(__file__).resolve().parent
    retained: list[str] = []
    for entry in sys.path:
        if entry in {"", "."}:
            continue
        try:
            resolved = Path(entry).resolve()
        except OSError:
            retained.append(entry)
            continue
        if resolved in {repo, script_dir}:
            continue
        retained.append(entry)
    sys.path = retained
    sys.path.insert(0, str(extract_root))


class _PackagedPyzLoader:
    def __init__(self, archive: ZlibArchiveReader, name: str, root: Path, is_package: bool) -> None:
        self._archive = archive
        self._name = name
        self._is_package = is_package
        if is_package:
            self.path = str(root.joinpath(*name.split(".")) / "__init__.py")
        else:
            self.path = str(root.joinpath(*name.split("."))) + ".py"

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        del spec
        return None

    def exec_module(self, module: object) -> None:
        module.__file__ = self.path  # type: ignore[attr-defined]
        code = self._archive.extract(self._name)
        exec(code, module.__dict__)  # type: ignore[attr-defined]


class _PackagedPyzFinder:
    def __init__(self, archive: ZlibArchiveReader, root: Path) -> None:
        self._archive = archive
        self._root = root

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del path, target
        if fullname in sys.stdlib_module_names or fullname.split(".", 1)[0] in sys.stdlib_module_names:
            return None
        entry = self._archive.toc.get(fullname)
        if entry is None:
            return None
        typecode = entry[0]
        if typecode == PYZ_ITEM_NSPKG:
            spec = importlib.machinery.ModuleSpec(fullname, None, is_package=True)
            spec.submodule_search_locations = [str(self._root.joinpath(*fullname.split(".")))]
            return spec
        is_package = typecode == PYZ_ITEM_PKG
        loader = _PackagedPyzLoader(self._archive, fullname, self._root, is_package)
        spec = importlib.machinery.ModuleSpec(fullname, loader, is_package=is_package, origin=loader.path)
        spec.has_location = True
        if is_package:
            spec.submodule_search_locations = [str(Path(loader.path).parent)]
        return spec


def _load_script_module(reader: CArchiveReader, name: str, extract_root: Path) -> types.ModuleType:
    code = marshal.loads(reader.extract(name))
    module = types.ModuleType(name)
    module.__file__ = str(extract_root / f"{name}.py")
    module.__package__ = ""
    module.__loader__ = None
    sys.modules[name] = module
    exec(code, module.__dict__)
    return module


def _install_packaged_importer(executable_pyz: str, extract_root: Path) -> None:
    archive = ZlibArchiveReader(executable_pyz, check_pymagic=True)
    sys.meta_path.insert(0, _PackagedPyzFinder(archive, extract_root))


def _block_dialogs() -> None:
    import tkinter.messagebox as messagebox

    def _dialog(title: str = "", message: str = "", *_args: object, **_kwargs: object) -> None:
        raise RuntimeError(f"DIALOG {title}: {message}")

    messagebox.showerror = _dialog
    messagebox.showwarning = _dialog
    messagebox.showinfo = _dialog
    messagebox.askyesno = lambda *_args, **_kwargs: False
    messagebox.askokcancel = lambda *_args, **_kwargs: False


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python tools/packaged_lineage_runtime_probe.py <executable>", file=sys.stderr)
        return 2
    executable = Path(argv[0]).resolve()
    if not executable.is_file():
        print(f"Missing executable: {executable}", file=sys.stderr)
        return 2
    extract_root = Path(tempfile.mkdtemp(prefix="sc900-packaged-runtime-"))
    local_app_data = Path(tempfile.mkdtemp(prefix="sc900-isolated-localappdata-"))
    receipt: dict[str, object] = {
        "artifact_path": str(executable),
        "artifact_sha256": _sha256(executable),
        "extract_root": str(extract_root),
        "localappdata": str(local_app_data),
    }
    try:
        reader = CArchiveReader(str(executable))
        receipt["extracted_members"] = _extract_packaged_files(reader, extract_root)
        os.environ["LOCALAPPDATA"] = str(local_app_data)
        sys._MEIPASS = str(extract_root)  # type: ignore[attr-defined]
        sys.frozen = True  # type: ignore[attr-defined]
        sys._pyinstaller_pyz = _pyz_offset(reader, executable)  # type: ignore[attr-defined]
        _isolate_import_path(extract_root)
        _install_packaged_importer(sys._pyinstaller_pyz, extract_root)  # type: ignore[attr-defined]
        _block_dialogs()
        import tkinter as tk

        import content_revision_registry as registry

        module_file = Path(registry.__file__).resolve()
        receipt["packaged_registry_file"] = str(module_file)
        receipt["packaged_registry_contained"] = _contained(module_file, extract_root)
        if not receipt["packaged_registry_contained"]:
            raise RuntimeError("Lineage module was not loaded from the extracted executable.")
        evidence_root = Path(registry.CONTENT_REVISION_EVIDENCE_ROOT).resolve()
        receipt["packaged_evidence_root"] = str(evidence_root)
        receipt["packaged_evidence_contained"] = _contained(evidence_root, extract_root)
        if not receipt["packaged_evidence_contained"]:
            raise RuntimeError("Lineage evidence root is outside the extracted executable.")

        lineage = registry.reconstruct_registered_lineage()
        admitted = isinstance(lineage, registry.RegisteredContentLineage)
        receipt["lineage_admitted"] = admitted
        if admitted:
            receipt["bank_count"] = len(lineage.bank_filenames)
            receipt["revision_count"] = len(lineage.revisions)
            receipt["first_bank"] = lineage.bank_filenames[0]
            receipt["final_bank"] = lineage.bank_filenames[-1]
            receipt["lineage_reasons"] = []
        else:
            receipt["bank_count"] = None
            receipt["revision_count"] = None
            receipt["first_bank"] = None
            receipt["final_bank"] = None
            receipt["lineage_reasons"] = [str(reason) for reason in getattr(lineage, "reasons", ())]

        app_module = _load_script_module(reader, "app", extract_root)

        user_data = Path(app_module.USER_DATA_DIR).resolve()
        receipt["effective_progress_storage_path"] = str(user_data)
        receipt["effective_progress_storage_contained"] = _contained(user_data, local_app_data)
        if not receipt["effective_progress_storage_contained"]:
            raise RuntimeError("Progress storage is outside the isolated LOCALAPPDATA root.")

        root = tk.Tk()
        root.withdraw()
        application = app_module.TestingEngineApp(root)
        receipt["window_title"] = str(application.root.title())
        receipt["question_count"] = len(application.master_questions)
        receipt["progress_write_blocked"] = bool(application.progress_write_blocked)
        receipt["loaded_bank"] = Path(application.bank_path).name if application.bank_path else ""
        log_path = Path(app_module.LOG_PATH)
        log_text = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        receipt["registry_hash_mismatch_logged"] = "REGISTRY_HASH_MISMATCH" in log_text
        receipt["lineage_warning_logged"] = "Registered content lineage was not admitted" in log_text

        progress_path = Path(application.progress_path) if application.progress_path else None
        receipt["progress_path"] = str(progress_path) if progress_path else ""
        if progress_path is not None and not _contained(progress_path, local_app_data):
            raise RuntimeError("Progress file path is outside the isolated LOCALAPPDATA root.")

        if application.progress_write_blocked or not application.master_questions:
            receipt["isolated_progress_save"] = "BLOCKED" if application.progress_write_blocked else "NO_QUESTIONS"
            receipt["isolated_progress_reload"] = "NOT_RUN"
            receipt["progress_file_created"] = bool(progress_path and progress_path.is_file())
        else:
            question = application.master_questions[0]
            question_id = application._question_key(question)
            selected = [str(letter) for letter in question.get("correct", [])]
            if not selected:
                raise RuntimeError("Production question has no correct choice to record.")
            application.gamification_enabled_var.set(False)
            application.boss_rounds_enabled_var.set(False)
            application.celebration_popups_var.set(False)
            application._record_answer(
                question,
                selected,
                feedback_override={"confidence": "Sure", "miss_reason": ""},
            )
            application.flush_scheduled_progress_save()
            created = bool(progress_path and progress_path.is_file())
            receipt["progress_file_created"] = created
            saved_payload: dict[str, object] = {}
            if created and progress_path is not None:
                saved_payload = json.loads(progress_path.read_text(encoding="utf-8"))
            receipt["saved_bank_file"] = saved_payload.get("bank_file")
            history = saved_payload.get("history")
            fingerprint_present = False
            if isinstance(history, list):
                fingerprint_present = any(
                    isinstance(event, dict) and str(event.get("question_content_fingerprint") or "").strip()
                    for event in history
                )
            receipt["saved_question_fingerprint_present"] = fingerprint_present
            receipt["isolated_progress_save"] = "PASS" if created and fingerprint_present else "FAIL"
            application.load_from_path(Path(application.bank_path))
            restored = application._progress_questions().get(question_id)
            reloaded = (
                json.loads(progress_path.read_text(encoding="utf-8"))
                if progress_path and progress_path.is_file()
                else {}
            )
            receipt["reloaded_bank_fingerprint"] = reloaded.get("bank_fingerprint")
            receipt["reloaded_bank_file"] = reloaded.get("bank_file")
            terminal = application.content_revision_lineage[-1] if application.content_revision_lineage else None
            expected_fingerprint = terminal.target_node.runtime_bank_fingerprint if terminal is not None else ""
            receipt["expected_bank_fingerprint"] = expected_fingerprint
            receipt["progress_write_blocked_after_reload"] = bool(application.progress_write_blocked)
            receipt["isolated_progress_reload"] = (
                "PASS"
                if isinstance(restored, dict)
                and int(restored.get("attempts") or 0) >= 1
                and reloaded.get("bank_fingerprint") == expected_fingerprint
                and reloaded.get("bank_file") == receipt["final_bank"]
                and not application.progress_write_blocked
                else "FAIL"
            )
        try:
            if application.smart_practice_prewarm is not None:
                application.smart_practice_prewarm.close()
        finally:
            application.root.destroy()
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    failed = receipt.get("isolated_progress_save") == "FAIL" or receipt.get("isolated_progress_reload") == "FAIL"
    return 1 if failed or not receipt.get("lineage_admitted") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
