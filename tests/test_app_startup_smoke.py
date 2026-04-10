import importlib.util
import socket
import subprocess
import sys
import time
import unittest

from grade_engine.enums import TOOL_FAMILIES

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class AppStartupSmokeTests(unittest.TestCase):
    def test_streamlit_testing_module_is_available(self):
        self.assertIsNotNone(importlib.util.find_spec("streamlit.testing.v1"))

    def test_streamlit_headless_startup_uses_free_port(self):
        port = _get_free_port()
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless",
                "true",
                "--server.port",
                str(port),
                "--browser.gatherUsageStats",
                "false",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=".",
        )
        output = ""

        try:
            deadline = time.time() + 20
            while time.time() < deadline:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                output += line
                if f"http://localhost:{port}" in line:
                    break
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()

        self.assertIn(f"http://localhost:{port}", output)


@unittest.skipIf(AppTest is None, "streamlit.testing.v1 is unavailable")
class AppUiFlowTests(unittest.TestCase):
    def _run_app_for_family(self, tool_family: str, show_internal: bool = False):
        app = AppTest.from_file("app.py")
        app.run()
        app.selectbox[0].set_value(tool_family)
        if show_internal:
            app.checkbox[0].check()
        app.run()
        return app

    def test_every_tool_family_builds_visible_recommendation_flow(self):
        for tool_family in TOOL_FAMILIES:
            with self.subTest(tool_family=tool_family):
                app = self._run_app_for_family(tool_family)
                subheaders = [item.value for item in app.subheader]
                self.assertIn("Recommendation", subheaders)
                self.assertIn("Starter Setup", subheaders)
                self.assertIn("Why this was chosen", subheaders)
                self.assertIn("What to watch", subheaders)
                self.assertIn("Behavior Readout", subheaders)
                self.assertIn("Supplier Search", subheaders)
                if tool_family == "TURNING_INSERT":
                    self.assertIn("Turning Insert Identity", subheaders)
                else:
                    self.assertNotIn("Turning Insert Identity", subheaders)

                self.assertEqual(len(app.button), 0)
                self.assertEqual(len(app.metric), 3 if tool_family != "TURNING_INSERT" else 7)
                self.assertEqual(len(app.info), 3 if tool_family != "TURNING_INSERT" else 4)
                self.assertEqual(len(app.get("link_button")), 4)
                self.assertTrue(all(button.url for button in app.get("link_button")))
                self.assertGreaterEqual(len(app.code), 4)

    def test_family_specific_controls_render_when_needed(self):
        threading_app = self._run_app_for_family("THREADING_INSERT")
        tap_app = self._run_app_for_family("TAP")
        reamer_app = self._run_app_for_family("REAMER")

        threading_labels = [item.label for item in threading_app.selectbox]
        tap_labels = [item.label for item in tap_app.selectbox]
        reamer_labels = [item.label for item in reamer_app.selectbox]

        self.assertIn("Thread Profile", threading_labels)
        self.assertIn("Thread Orientation", threading_labels)
        self.assertIn("Hole Type", tap_labels)
        self.assertIn("Hole Type", reamer_labels)

    def test_internal_logic_toggle_reveals_logic_key_code_block(self):
        app = self._run_app_for_family("TURNING_INSERT", show_internal=True)

        captions = [item.value for item in app.caption]
        code_blocks = [item.value for item in app.code]

        self.assertIn("Internal logic key", captions)
        self.assertTrue(any(code_block.startswith("P_") and "_T_" in code_block for code_block in code_blocks))


if __name__ == "__main__":
    unittest.main()
