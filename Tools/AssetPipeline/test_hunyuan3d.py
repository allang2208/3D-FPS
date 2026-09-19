"""Offline contract tests. No credentials, API calls or generation charges."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hunyuan3d as api


class WorkflowTests(unittest.TestCase):
    def test_business_error_even_http_200(self):
        with self.assertRaises(RuntimeError):
            api.check(200, {"error": {"code": "FailedOperation.JobNotFound"}})

    def test_legacy_business_error(self):
        with self.assertRaises(RuntimeError):
            api.check(200, {"Response": {"Error": {"Code": "ResourceInsufficient"}}})

    def test_provider_query_contract(self):
        for provider, expected in [("tokenhub", {"id": "test", "model": "hy-3d-3.1"}), ("legacy", {"JobId": "test"})]:
            with patch.object(api, "post", return_value=(200, {"status": "queued"})) as post:
                api.query({"provider": provider, "job_id": "test", "model": "3.1"})
                self.assertEqual(post.call_args.args, (provider, "query", expected))

    def test_response_redacts_credential(self):
        response = io.BytesIO(b'{"error":"fake-test-secret"}')
        response.status = 200
        with patch.object(api, "credential", return_value="fake-test-secret"), patch.object(api.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            code, data = api.post("tokenhub", "query", {})
            self.assertNotIn("fake-test-secret", json.dumps(data))
            self.assertIn("REDACTED", json.dumps(data))

    def test_timeout_submit_not_retried_and_manifest_retained(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(api, "ROOT", Path(tmp)), patch.object(api, "post", side_effect=TimeoutError("network")) as post, patch("sys.argv", ["hunyuan3d", "submit", "--name", "candidate", "--prompt", "test"]):
            with self.assertRaises(TimeoutError):
                api.main()
            self.assertEqual(post.call_count, 1)
            record = json.loads((Path(tmp) / "Saved/Hunyuan3D/Candidates/candidate/manifest.json").read_text())
            self.assertEqual(record["stage"], "submission_pending")

    def test_download_failure_does_not_mark_complete(self):
        record = {"provider": "tokenhub"}
        with tempfile.TemporaryDirectory() as tmp, patch.object(api.urllib.request, "urlopen", side_effect=OSError("network")):
            with self.assertRaises(OSError):
                api.download(record, {"data": [{"url": "https://example.test/model.glb"}]}, Path(tmp))
        self.assertNotIn("outputs", record)

    def test_failed_job_stops_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            api.save(manifest, {"provider": "legacy", "job_id": "test", "model": "3.1"})
            with patch.object(api, "query", return_value={"Status": "FAIL"}), patch.object(api, "download") as download, patch("sys.argv", ["hunyuan3d", "resume", "--manifest", str(manifest)]), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):
                    api.main()
                download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
