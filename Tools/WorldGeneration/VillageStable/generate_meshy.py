"""Generate the nine Design01 stable components using independent orthographic images."""
import argparse
import functools
import hashlib
import ipaddress
import subprocess
import tempfile
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import getpass
import importlib.util
import json
import msvcrt
import os
from pathlib import Path
import sys
import time

import requests

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/HillsVillageStable"
BATCH = SOURCE / "MeshyR1"
PARTS = json.loads((SOURCE / "Design01/image-directions.json").read_text(encoding="utf-8"))["components"]
MODEL = "meshy-7.1"
ENDPOINT = "/v1/multi-image-to-3d"
PARAMETERS = {"ai_model": MODEL, "geometry_resolution": "standard", "should_texture": True,
              "texture_model": "meshy-7", "texture_resolution": "2k",
              "enable_pbr": True, "target_formats": ["glb", "fbx"]}

spec = importlib.util.spec_from_file_location("meshy_client", PROJECT / "SourceAssets/WitchMeshy20260919/meshy_pipeline.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
api.ROOT, api.OUT = SOURCE, BATCH
api.SETTINGS.update(common=PARAMETERS, assets={
    p["id"]: {"images": [f"Design01/Components/{p['id']}/{v}.png" for v in
                         ("front", "right", "top" if p["id"] == "A09" else "back")], "options": {}}
    for p in PARTS})


@functools.lru_cache(maxsize=24)
def public_addresses(host):
    # Resolve through HTTPS. Keep the original hostname for TLS SNI and certificate checks.
    name = urllib.parse.quote(host, safe="")
    command = ["curl.exe", "-fsS", "--proxy", api.SETTINGS["proxy"],
               "--connect-timeout", "10", "--max-time", "20",
               "https://dns.google/resolve?type=A&name=" + name]
    result = subprocess.run(command, capture_output=True, check=True)
    return [str(ipaddress.IPv4Address(a["data"])) for a in json.loads(result.stdout).get("Answer", [])
            if a["type"] == 1]


def transfer(url, *, key=None, payload_file=None, destination=None):
    host = urllib.parse.urlsplit(url).hostname
    addresses = public_addresses(host)
    if not addresses:
        raise RuntimeError(f"No public IPv4 records for {host}")
    settings = "url = " + json.dumps(url) + "\n"
    if key:
        settings += "header = " + json.dumps("Authorization: Bearer " + key) + "\n"
    for address in addresses:
        args = ["curl.exe", "--silent", "--show-error", "--config", "-", "--proxy",
                api.SETTINGS["proxy"].replace("http://", "socks5://"), "--resolve",
                f"{host}:443:{address}", "--connect-timeout", "12", "--max-time", "300"]
        if payload_file:
            args.extend(["--header", "Content-Type: application/json", "--data-binary", "@"+payload_file])
        if destination:
            args.extend(["--fail","--location","--output",str(destination)])
        else:
            args.extend(["--write-out", "\n%{http_code}"])
        proc = subprocess.run(args, input=settings.encode(), capture_output=True)
        if proc.returncode == 0:
            if destination:
                return
            body, code = proc.stdout.rsplit(b"\n", 1)
            if not 200 <= int(code) < 300:
                raise RuntimeError(f"Meshy HTTP {code.decode()}: {api.safe(body.decode(errors='replace')[:600])}")
            return json.loads(body)
        if payload_file and proc.returncode not in (5, 6, 7, 35):
            break
    raise RuntimeError(f"Transfer of {host} failed: curl {proc.returncode} {api.safe(proc.stderr.decode(errors='replace'))}")


def mesh_request(method, endpoint, payload=None):
    if method == "GET":
        return transfer(api.API + endpoint, key=api.key_from_environment())
    with tempfile.NamedTemporaryFile(dir=BATCH, prefix="images-", suffix=".json", mode="w",
                                     encoding="utf-8", delete=False) as file:
        json.dump(payload, file)
    try:
        return transfer(api.API + endpoint, key=api.key_from_environment(), payload_file=file.name)
    finally:
        Path(file.name).unlink(missing_ok=True)


def download_files(folder, result):
    files = []
    for key in ("model_urls", "texture_urls", "thumbnail_url"):
        for parts, url in api.asset_urls(result.get(key), (key,)):
            suffix = Path(urllib.parse.urlsplit(url).path).suffix
            dest = folder / "downloads" / ("_".join(parts) + suffix)
            dest.parent.mkdir(exist_ok=True)
            if not dest.is_file():
                partial = dest.with_suffix(dest.suffix + ".part")
                transfer(url, destination=partial)
                partial.replace(dest)
            with dest.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            files.append({"file": str(dest.relative_to(SOURCE)), "bytes": dest.stat().st_size,
                          "sha256": digest, "source": api.safe(url)})
    api.write_json(folder / "downloads.json",files)


api.api = mesh_request


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def submit(part):
    folder = BATCH / part
    if (folder / "task.json").is_file():
        return
    # Retry a rejected request only when the API confirms a rate or queue limit.
    for attempt in range(180):
        try:
            api.submit(part)
            return
        except RuntimeError as exc:
            if "Meshy HTTP 429:" not in str(exc):
                raise
            request = folder / "request.json"
            if request.exists():
                request.replace(folder / "request-rate-limited.json")
            if attempt == 0:
                print(part, "waiting for queue capacity", flush=True)
            time.sleep(30)
    raise RuntimeError(f"{part}: Meshy queue limit persisted")


def collect(item):
    part = item["id"]
    folder = BATCH / part
    task = read(folder / "task.json")
    previous = None
    retries = 0
    while True:
        try:
            result = api.api("GET", ENDPOINT + "/" + task["task_id"])
            api.write_json(folder / "response.json", result)
            state = result["status"], result.get("progress")
            if state != previous:
                print(part, *state, flush=True)
                previous = state
            if state[0] in ("FAILED", "CANCELED"):
                return {"id": part, "name": item["name"], "status": state[0],
                        "task_id": task["task_id"], "error": api.safe(result.get("task_error"))}
            if state[0] == "SUCCEEDED":
                download_files(folder, result)
                files = read(folder / "downloads.json")
                models = [x["file"] for x in files if Path(x["file"]).suffix.lower() in (".glb", ".fbx")]
                if {Path(x).suffix.lower() for x in models} != {".glb", ".fbx"}:
                    raise RuntimeError("Missing requested model format")
                print(part, "downloaded", len(files), "files", flush=True)
                return {"id": part, "name": item["name"], "task_id": task["task_id"], "status": "SUCCEEDED",
                        "views": api.SETTINGS["assets"][part]["images"], "models": models,
                        "downloads": str((folder / "downloads.json").relative_to(SOURCE)),
                        "credits": result.get("consumed_credits"), "file_count": len(files)}
            retries = 0
        except (OSError, requests.exceptions.RequestException, RuntimeError) as exc:
            retries += 1
            print(part, "status/transfer retry", retries, api.safe(str(exc)), flush=True)
            if retries >= 12:
                raise
        time.sleep(20)


def run(receipt):
    try:
        api.key_from_environment()
    except RuntimeError:
        os.environ["MESHY_API_KEY"] = getpass.getpass("Meshy key (hidden): ").strip()
    api.balance("start")
    # Collect accepted tasks even if a later asset cannot be submitted.
    accepted = []
    with ThreadPoolExecutor(max_workers=4) as workers:
        for item in PARTS:
            try:
                submit(item["id"])
            except Exception as exc:
                print(item["id"], "submission stopped:", api.safe(str(exc)), flush=True)
                break
            accepted.append(workers.submit(collect, item))
        records = [job.result() for job in accepted]
    summary = {"model": MODEL, "endpoint": ENDPOINT, "parameters": PARAMETERS,
               "source_root": str(SOURCE.resolve()), "items": records,
               "credits_total": sum(r.get("credits") or 0 for r in records),
               "status": "complete" if len(records)==len(PARTS) and all(r["status"]=="SUCCEEDED" for r in records) else "partial"}
    api.write_json(receipt / "generated.json", summary)
    api.balance("end")
    print("batch",summary["status"],len(records),"tasks,",summary["credits_total"],"credits",flush=True)
    return summary["status"] == "complete"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    BATCH.mkdir(parents=True, exist_ok=True)
    with (BATCH / "batch.lock").open("a+b") as lock:
        if not lock.tell():
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            done = run(args.receipt)
        except Exception as exc:
            print(api.safe(str(exc)), file=sys.stderr, flush=True)
            sys.exit(1)
        sys.exit(0 if done else 2)
