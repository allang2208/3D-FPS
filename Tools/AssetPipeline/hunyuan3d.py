"""Tencent 3D candidate workflow. Standard library; credentials never in arguments."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = {
    "legacy": "https://api.ai3d.cloud.tencent.com/v1/ai3d/",
    "tokenhub": "https://tokenhub.tencentmaas.com/v1/api/3d/",
}


def credential():
    key = os.environ.get("HUNYUAN3D_API_KEY")
    if not key:
        script = "$p=Join-Path $env:LOCALAPPDATA 'FPSGAME\\Credentials\\hunyuan3d.dpapi'; $s=Get-Content -LiteralPath $p -ErrorAction Stop | ConvertTo-SecureString; [System.Net.NetworkCredential]::new('', $s).Password"
        result = subprocess.run(["pwsh", "-NoProfile", "-Command", "$ErrorActionPreference='Stop'; " + script], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Missing local credential; set HUNYUAN3D_API_KEY or use the DPAPI setup command in the guide")
        key = result.stdout.strip()
    if not key or any(c.isspace() for c in key):
        raise RuntimeError("Invalid credential format")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(provider, action, payload):
    key = credential()
    auth = "Bearer " + key if provider == "tokenhub" else key
    request = urllib.request.Request(ENDPOINTS[provider] + action,
        data=json.dumps(payload).encode(), headers={"Authorization": auth, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=45) as response:
            code, raw = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        code, raw = error.code, error.read().decode("utf-8", "replace")
    # Sanitize even unexpected upstream responses before returning or storing them.
    raw = raw.replace(key, "[REDACTED]")
    try:
        data = json.loads(raw)
    except ValueError:
        data = {"error": "Non-JSON response", "http_status": code}
    return code, data


def body(data):
    return data.get("Response", data)


def check(code, data):
    value = body(data)
    if code >= 300 or value.get("Error") or value.get("error"):
        raise RuntimeError(json.dumps({"http": code, "response": data}, ensure_ascii=False))
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def query(record):
    payload = {"id": record["job_id"], "model": "hy-3d-" + record["model"]} if record["provider"] == "tokenhub" else {"JobId": record["job_id"]}
    return check(*post(record["provider"], "query", payload))


def state(response):
    return str(response.get("status", response.get("Status", response.get("State", "")))).lower()


def download(record, response, folder):
    files = response.get("data", []) if record["provider"] == "tokenhub" else response.get("ResultFile3Ds", [])
    if not files:
        raise RuntimeError("Completed response has no asset files")
    outputs = []
    for index, item in enumerate(files):
        url = item.get("url", item.get("Url"))
        if not url or urllib.parse.urlsplit(url).scheme != "https":
            raise RuntimeError("Asset URL missing or not HTTPS")
        suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        if suffix not in {".glb", ".fbx", ".zip", ".obj", ".stl", ".usdz"}:
            raise RuntimeError("Unexpected asset extension")
        destination = folder / ("asset_%02d" % index + suffix)
        partial = destination.with_suffix(suffix + ".part")
        digest = hashlib.sha256()
        # No credential is ever attached to asset-download requests.
        with urllib.request.urlopen(url, timeout=60) as source, partial.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
                digest.update(chunk)
        if not partial.stat().st_size:
            raise RuntimeError("Empty asset download")
        partial.replace(destination)
        outputs.append({"file": destination.name, "bytes": destination.stat().st_size, "sha256": digest.hexdigest()})
    record["outputs"] = outputs
    record["stage"] = "candidate_downloaded"
    record["rigging_verified"] = False
    record["ue_runtime_verified"] = False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe", help="Query a nonexistent job; never submits generation")
    probe.add_argument("--provider", choices=ENDPOINTS, required=True)
    submit = sub.add_parser("submit")
    submit.add_argument("--provider", choices=ENDPOINTS, default="tokenhub")
    submit.add_argument("--model", choices=["3.0", "3.1"], default="3.1")
    submit.add_argument("--name", required=True)
    inputs = submit.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--image", type=Path)
    inputs.add_argument("--prompt")
    submit.add_argument("--pbr", action="store_true")
    resume = sub.add_parser("resume", help="Query/download an existing job without resubmitting")
    resume.add_argument("--manifest", type=Path, required=True)
    resume.add_argument("--wait", action="store_true")
    resume.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    if args.command == "probe":
        payload = {"id": "0000000000000000000", "model": "hy-3d-3.1"} if args.provider == "tokenhub" else {"JobId": "00000000-0000-0000-0000-000000000000"}
        code, data = post(args.provider, "query", payload)
        report = {"provider": args.provider, "http": code, "response": data, "generation_submitted": False}
        save(ROOT / "Saved/Hunyuan3D" / (args.provider + "-probe.json"), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if code < 300 else 1
    if args.command == "submit":
        if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.name):
            raise RuntimeError("Candidate name must contain only ASCII letters, digits, underscore or hyphen")
        folder = ROOT / "Saved/Hunyuan3D/Candidates" / args.name
        folder.mkdir(parents=True, exist_ok=False)
        manifest = folder / "manifest.json"
        record = {"provider": args.provider, "model": args.model, "stage": "prepared", "created_at": time.time()}
        payload = {"model": "hy-3d-" + args.model} if args.provider == "tokenhub" else {"Model": args.model}
        if args.image:
            raw = args.image.read_bytes()
            if len(raw) > 6 * 1024 * 1024 or args.image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise RuntimeError("Input must be PNG/JPEG/WebP, at most 6 MiB")
            encoded = base64.b64encode(raw).decode()
            record["source"] = {"path": str(args.image.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}
            mime = {".png": "image/png", ".webp": "image/webp"}.get(args.image.suffix.lower(), "image/jpeg")
            payload["image_base64" if args.provider == "tokenhub" else "ImageUrl"] = encoded if args.provider == "tokenhub" else "data:" + mime + ";base64," + encoded
        else:
            if len(args.prompt) > 1024:
                raise RuntimeError("Prompt exceeds 1024 characters")
            record["prompt"] = args.prompt
            payload["prompt" if args.provider == "tokenhub" else "Prompt"] = args.prompt
        if args.pbr:
            payload["enable_pbr" if args.provider == "tokenhub" else "EnablePBR"] = True
        record["pbr"] = args.pbr
        save(manifest, record)
        # Submit only once. Network uncertainty must not create duplicate paid jobs.
        record["stage"] = "submission_pending"
        save(manifest, record)
        response = check(*post(args.provider, "submit", payload))
        job_id = response.get("id", response.get("JobId"))
        if not job_id:
            raise RuntimeError("Submission returned no job ID; do not automatically retry")
        record.update(job_id=job_id, stage="submitted", submit_response=response)
        save(manifest, record)
        print(str(manifest))
        return 0
    manifest = args.manifest.resolve()
    record = json.loads(manifest.read_text(encoding="utf-8"))
    deadline = time.monotonic() + args.timeout
    while True:
        response = query(record)
        current = state(response)
        record.update(last_response=response, stage=current, checked_at=time.time())
        save(manifest, record)
        print("Job state:", current, flush=True)
        if current in {"done", "completed", "success", "succeed"}:
            download(record, response, manifest.parent)
            save(manifest, record)
            return 0
        if current in {"fail", "failed", "error", "cancelled"}:
            raise RuntimeError("Generation failed; see local manifest")
        if current not in {"wait", "run", "queued", "in_progress", "waiting", "running"}:
            raise RuntimeError("Unknown job state; see local manifest")
        if not args.wait:
            return 0
        if time.monotonic() >= deadline:
            raise RuntimeError("Polling timed out; resume with this manifest, do not resubmit")
        time.sleep(10)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as error:
        print("Error:", str(error), file=sys.stderr)
        sys.exit(1)
