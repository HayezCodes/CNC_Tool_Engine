import socket
import subprocess
import sys
import time
import unittest


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class AppStartupSmokeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
