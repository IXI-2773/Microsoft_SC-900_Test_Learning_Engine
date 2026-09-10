import importlib.util
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from application_bootstrap import BootstrapConfig, prepare_application_bootstrap
from storage_utils import safe_write_json, setup_logging

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def test_prepare_application_bootstrap_runs_side_effects_only_on_explicit_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = BootstrapConfig(
                user_data_dir=root / "user_data",
                checkpoint_dir=root / "user_data" / "checkpoints",
                backup_dir=root / "user_data" / "backups",
                log_base_dir=root / "logs",
            )
            migrated = []
            logged = []

            def migrate_runtime(path: Path) -> str:
                migrated.append(path)
                return "migrated"

            def setup_logging_fn(path: Path) -> Path:
                logged.append(path)
                return path / "logs" / "sc900_test_learning_engine.log"

            self.assertFalse(config.user_data_dir.exists())
            result = prepare_application_bootstrap(
                config,
                migrate_runtime=migrate_runtime,
                setup_logging_fn=setup_logging_fn,
            )

            self.assertTrue(config.user_data_dir.exists())
            self.assertEqual([config.user_data_dir], migrated)
            self.assertEqual([config.log_base_dir], logged)
            self.assertEqual("migrated", result.runtime_migration_notice)

    def test_setup_logging_creates_missing_parent_log_directory(self):
        root = logging.getLogger()
        previous_handlers = list(root.handlers)
        previous_level = root.level
        storage_logger = logging.getLogger("storage_utils")
        previous_propagate = storage_logger.propagate

        def restore_logging():
            for handler in list(root.handlers):
                root.removeHandler(handler)
                handler.close()
            for handler in previous_handlers:
                root.addHandler(handler)
            root.setLevel(previous_level)
            storage_logger.propagate = previous_propagate

        with tempfile.TemporaryDirectory() as tmp:
            try:
                base = Path(tmp) / "user_data"
                log_path = setup_logging(base)
                self.assertTrue((base / "logs").is_dir())
                self.assertEqual(base / "logs" / "sc900_test_learning_engine.log", log_path)
            finally:
                restore_logging()
        with tempfile.TemporaryDirectory() as tmp:
            written = Path(tmp) / "ok.json"
            safe_write_json(written, {"ok": True})
            self.assertTrue(written.exists())

    def test_importing_app_module_does_not_bootstrap_runtime(self):
        app_path = ROOT / "app.py"
        module_name = "test_app_import_no_bootstrap"
        spec = importlib.util.spec_from_file_location(module_name, app_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.pop(module_name, None)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        with (
            mock.patch("pathlib.Path.mkdir") as mkdir_mock,
            mock.patch("storage_utils.setup_logging") as setup_logging_mock,
        ):
            spec.loader.exec_module(module)
        self.assertFalse(mkdir_mock.called)
        self.assertFalse(setup_logging_mock.called)


if __name__ == "__main__":
    unittest.main()
