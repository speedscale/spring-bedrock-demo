import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import threading
import unittest


spec = importlib.util.spec_from_file_location("traffic_client", Path(__file__).parents[1] / "traffic-client.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class TrafficClientTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.fail = False
        self.malformed = False
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.respond(None)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.respond(body)

            def respond(self, body):
                test.calls.append((self.command, self.path, body, self.headers.get("X-Demo-Run")))
                status, payload = 200, {"status": "UP"}
                if self.command == "POST":
                    status, payload = (200, {"response": "Use the reset link."}) if body.get("prompt") else (400, {"error": "Prompt is required"})
                if test.fail:
                    status, payload = 503, {"error": "Bedrock unavailable"}
                self.send_response(status)
                self.send_header("Content-Type", "application/vnd.spring-boot.actuator.v3+json" if self.command == "GET" else "application/json")
                self.end_headers()
                self.wfile.write(b"not json" if test.malformed else json.dumps(payload).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_client(self, count):
        with contextlib.redirect_stdout(io.StringIO()):
            return client.run(self.url, count, 0, 1, "test-run")

    def test_finite_mix_covers_success_validation_and_health(self):
        result = self.run_client(7)
        self.assertEqual(7, len(self.calls))
        self.assertEqual(7, result["passed"])
        self.assertEqual(4, result["bedrock_chat_attempts"])
        self.assertEqual({"200": 5, "400": 2}, result["statuses"])
        self.assertEqual([], result["failures"])
        self.assertTrue(all(call[3] == "test-run" for call in self.calls))

    def test_unexpected_failure_stops_without_retries(self):
        self.fail = True
        result = self.run_client(8)
        self.assertEqual(1, len(self.calls))
        self.assertEqual(0, result["passed"])
        self.assertEqual(1, len(result["failures"]))

    def test_invalid_json_is_not_a_success(self):
        self.malformed = True
        result = self.run_client(8)
        self.assertEqual(1, len(self.calls))
        self.assertEqual(0, result["passed"])
        self.assertEqual(1, len(result["failures"]))


if __name__ == "__main__":
    unittest.main()
