import importlib.util
import pathlib
import sys
import types
import unittest


def install_qgis_stubs():
    if "qgis" in sys.modules:
        return

    qgis_module = types.ModuleType("qgis")
    pyqt_module = types.ModuleType("qgis.PyQt")
    qtcore_module = types.ModuleType("qgis.PyQt.QtCore")
    qtwidgets_module = types.ModuleType("qgis.PyQt.QtWidgets")

    class Signal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)

    class StubQProcess:
        NotRunning = 0
        Running = 2
        detached_result = (True, 1234)
        wait_for_started_result = True
        detached_calls = []
        created_instances = []

        @staticmethod
        def startDetached(program, arguments):
            StubQProcess.detached_calls.append((program, arguments))
            return StubQProcess.detached_result

        def __init__(self, parent=None):
            self.parent = parent
            self.finished = Signal()
            self.errorOccurred = Signal()
            self._state = self.NotRunning
            self.started_program = None
            self.started_arguments = None
            StubQProcess.created_instances.append(self)

        def start(self, program, arguments):
            self.started_program = program
            self.started_arguments = arguments
            self._state = self.Running
            return None

        def waitForStarted(self, _timeout=0):
            return self.wait_for_started_result

        def state(self):
            return self._state

    class StubQProgressDialog:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.window_title = None
            self.auto_close = None
            self.modal = None
            self.visible = False
            self.closed = False

        def setWindowTitle(self, title):
            self.window_title = title

        def setAutoClose(self, value):
            self.auto_close = value

        def setModal(self, value):
            self.modal = value

        def show(self):
            self.visible = True

        def close(self):
            self.closed = True

    qtcore_module.QProcess = StubQProcess
    qtwidgets_module.QProgressDialog = StubQProgressDialog
    pyqt_module.QtCore = qtcore_module
    pyqt_module.QtWidgets = qtwidgets_module
    qgis_module.PyQt = pyqt_module

    sys.modules["qgis"] = qgis_module
    sys.modules["qgis.PyQt"] = pyqt_module
    sys.modules["qgis.PyQt.QtCore"] = qtcore_module
    sys.modules["qgis.PyQt.QtWidgets"] = qtwidgets_module


class FakeLogUtils:
    created = []

    def __init__(self, *, tool, class_name, level="INFO"):
        self.tool = tool
        self.class_name = class_name
        self.level = level
        self.records = []
        FakeLogUtils.created.append(self)

    def debug(self, msg, *, code=None, **data):
        self.records.append(("DEBUG", msg, code, data))

    def info(self, msg, *, code=None, **data):
        self.records.append(("INFO", msg, code, data))

    def warning(self, msg, *, code=None, **data):
        self.records.append(("WARNING", msg, code, data))

    def error(self, msg, *, code=None, **data):
        self.records.append(("ERROR", msg, code, data))

    def exception(self, exc, *, code=None, **data):
        payload = dict(data)
        payload["exception_type"] = type(exc).__name__
        payload["exception_message"] = str(exc)
        self.records.append(("EXCEPTION", "Unhandled exception", code, payload))


class FakeToolKey:
    UNTRACEABLE = "untraceable"
    EXPORT_ALL_LAYOUTS = "export_all_layouts"


install_qgis_stubs()

project_root = pathlib.Path(__file__).resolve().parents[1]

cadmus_package = types.ModuleType("Cadmus")
cadmus_package.__path__ = [str(project_root)]
sys.modules["Cadmus"] = cadmus_package

cadmus_utils_package = types.ModuleType("Cadmus.utils")
cadmus_utils_package.__path__ = [str(project_root / "utils")]
sys.modules["Cadmus.utils"] = cadmus_utils_package

cadmus_core_package = types.ModuleType("Cadmus.core")
cadmus_core_package.__path__ = [str(project_root / "core")]
sys.modules["Cadmus.core"] = cadmus_core_package

cadmus_core_config_package = types.ModuleType("Cadmus.core.config")
cadmus_core_config_package.__path__ = [str(project_root / "core" / "config")]
sys.modules["Cadmus.core.config"] = cadmus_core_config_package

toolkeys_module = types.ModuleType("Cadmus.utils.ToolKeys")
toolkeys_module.ToolKey = FakeToolKey
sys.modules["Cadmus.utils.ToolKeys"] = toolkeys_module

logutils_module = types.ModuleType("Cadmus.core.config.LogUtils")
logutils_module.LogUtils = FakeLogUtils
sys.modules["Cadmus.core.config.LogUtils"] = logutils_module

module_path = project_root / "utils" / "DependenciesManager.py"
module_spec = importlib.util.spec_from_file_location(
    "Cadmus.utils.DependenciesManager", module_path
)
dm_module = importlib.util.module_from_spec(module_spec)
sys.modules["Cadmus.utils.DependenciesManager"] = dm_module
module_spec.loader.exec_module(dm_module)


class FakeIface:
    def mainWindow(self):
        return "fake-main-window"


class DependenciesManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = dm_module.DependenciesManager
        self.original_dependencies = self.manager.DEPENDENCIES
        self.original_qprocess = dm_module.QProcess
        self.original_progress_dialog = dm_module.QProgressDialog
        self.toolkey = FakeToolKey.EXPORT_ALL_LAYOUTS

        FakeLogUtils.created.clear()
        dm_module.QProcess.detached_calls.clear()
        dm_module.QProcess.created_instances.clear()
        dm_module.QProcess.detached_result = (True, 1234)
        dm_module.QProcess.wait_for_started_result = True

    def tearDown(self):
        self.manager.DEPENDENCIES = self.original_dependencies
        dm_module.QProcess = self.original_qprocess
        dm_module.QProgressDialog = self.original_progress_dialog
        if hasattr(self.manager, "_active_processes"):
            self.manager._active_processes.clear()

    def _last_logger(self):
        return FakeLogUtils.created[-1]

    def _all_records(self):
        records = []
        for logger in FakeLogUtils.created:
            records.extend(logger.records)
        return records

    def test_get_logger_uses_provided_toolkey(self):
        logger = self.manager.get_logger(self.toolkey)

        self.assertEqual(logger.tool, self.toolkey)
        self.assertEqual(logger.class_name, "DependenciesManager")

    def test_check_dependency_and_validation(self):
        self.manager.DEPENDENCIES = {
            "JsonLib": {
                "import": "json",
                "script": "unused.cmd",
                "description": "json",
                "pip": "json",
            },
            "MissingLib": {
                "import": "cadmus_dependency_missing_for_test",
                "script": "unused.cmd",
                "description": "missing",
                "pip": "missing",
            },
        }

        self.assertTrue(self.manager.check_dependency("JsonLib", self.toolkey))
        self.assertFalse(self.manager.check_dependency("MissingLib", self.toolkey))
        self.assertFalse(self.manager.check_dependency("UnknownLib", self.toolkey))

        result = self.manager.validate_dependencies(
            ["JsonLib", "MissingLib"], self.toolkey
        )
        self.assertFalse(result["all_present"])
        self.assertEqual(result["present"], ["JsonLib"])
        self.assertEqual(result["missing"], ["MissingLib"])

    def test_install_dependency_supports_unmapped_library_name(self):
        started = self.manager.install_dependency("bandit", self.toolkey)

        self.assertTrue(started)
        self.assertEqual(len(dm_module.QProcess.detached_calls), 1)
        self.assertEqual(
            dm_module.QProcess.detached_calls[0][1][-1],
            "bandit",
        )

    def test_install_dependency_handles_startdetached_tuple_success(self):
        self.manager.DEPENDENCIES = {
            "JsonLib": {
                "import": "json",
                "script": "unused.cmd",
                "description": "json",
                "pip": "json",
            }
        }

        started = self.manager.install_dependency("JsonLib", self.toolkey)

        self.assertTrue(started)
        self.assertEqual(len(dm_module.QProcess.detached_calls), 1)
        self.assertEqual(self._last_logger().tool, self.toolkey)

    def test_install_dependency_handles_startdetached_tuple_failure(self):
        self.manager.DEPENDENCIES = {
            "BrokenLib": {
                "import": "broken",
                "script": "unused.cmd",
                "description": "broken",
                "pip": "broken",
            }
        }
        dm_module.QProcess.detached_result = (False, 0)

        started = self.manager.install_dependency("BrokenLib", self.toolkey)

        self.assertFalse(started)
        self.assertIn(
            (
                "ERROR",
                "Falha ao iniciar processo de instalação",
                "INSTALL_DEPENDENCY_START_FAILED",
                {
                    "dependency_name": "BrokenLib",
                    "pip_name": "broken",
                    "python_executable": sys.executable,
                },
            ),
            self._all_records(),
        )

    def test_install_dependency_gui_returns_true_when_process_starts(self):
        self.manager.DEPENDENCIES = {
            "JsonLib": {
                "import": "json",
                "script": "unused.cmd",
                "description": "json",
                "pip": "json",
            }
        }

        started = self.manager.install_dependency_gui(
            "JsonLib", FakeIface(), self.toolkey
        )

        self.assertTrue(started)
        self.assertEqual(len(dm_module.QProcess.created_instances), 1)
        proc = dm_module.QProcess.created_instances[0]
        self.assertEqual(
            proc.started_arguments,
            [
                "-m",
                "pip",
                "install",
                "--user",
                "--disable-pip-version-check",
                "json",
            ],
        )

    def test_install_dependency_gui_reports_failure_to_start(self):
        self.manager.DEPENDENCIES = {
            "JsonLib": {
                "import": "json",
                "script": "unused.cmd",
                "description": "json",
                "pip": "json",
            }
        }
        dm_module.QProcess.wait_for_started_result = False

        started = self.manager.install_dependency_gui(
            "JsonLib", FakeIface(), self.toolkey
        )

        self.assertFalse(started)


if __name__ == "__main__":
    unittest.main()
