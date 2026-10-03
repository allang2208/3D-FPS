"""Acquire the requested RSH-12 from a local package or the official Download API.

Account credentials and signed download URLs are never persisted or printed.
This is source acquisition only; it does not import assets or publish runtime data.
"""
import argparse
import getpass
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UID = "177cd570002d4e89bd378ec328a47f9c"
PAGE = "https://sketchfab.com/3d-models/rsh-12-" + UID
API = "https://api.sketchfab.com/v3/models/" + UID
ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / "Original"


def request_json(url, authorization=None):
    headers = {"User-Agent": "FPSGAME-AssetAcquisition/1.0"}
    if authorization:
        headers["Authorization"] = authorization
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
        return json.load(response)


def save_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Local ZIP/GLB/glTF/FBX/OBJ/Blend package")
    parser.add_argument("--prompt", action="store_true", help="Read the API credential privately from stdin")
    args = parser.parse_args()
    metadata = request_json(API)
    save_json("sketchfab_metadata.json", metadata)
    if metadata.get("license", {}).get("slug") != "by":
        raise SystemExit("The source license has changed; acquisition stopped.")
    ORIGINAL.mkdir(exist_ok=True)
    if args.source:
        source = args.source.resolve(strict=True)
        if not source.is_file():
            raise SystemExit("Supply a source file, not a directory.")
        if source.suffix.lower() not in (".zip", ".glb", ".gltf", ".fbx", ".obj", ".blend"):
            raise SystemExit("Unsupported source package extension.")
        archive = ORIGINAL / source.name
        if archive.resolve() != source:
            shutil.copy2(source, archive)
        # Adjacent glTF/OBJ references must be supplied together as a ZIP.
        method = "User-provided local source package"
    else:
        token = getpass.getpass("Sketchfab API credential: ").strip() if args.prompt else os.environ.get("SKETCHFAB_TOKEN", "").strip()
        if not token:
            raise SystemExit("Source required: provide --source PATH or configure SKETCHFAB_TOKEN locally.")
        download = None
        for scheme in ("Token", "Bearer"):
            try:
                download = request_json(API + "/download", scheme + " " + token)
                break
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise
        token = None
        if not download:
            raise SystemExit("Sketchfab authentication rejected (HTTP 401).")
        fmt = next((key for key in ("source", "glb", "gltf") if download.get(key, {}).get("url")), None)
        if not fmt:
            raise SystemExit("No downloadable source format returned by the official API.")
        entry = download[fmt]
        from urllib.parse import urlsplit
        extension = Path(urlsplit(entry["url"]).path).suffix.lower()
        archive = ORIGINAL / ("RSH12_Official" + (extension or (".glb" if fmt == "glb" else ".zip")))
        request = urllib.request.Request(entry["url"], headers={"User-Agent": "FPSGAME-AssetAcquisition/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as dest:
            shutil.copyfileobj(response, dest)
        method = "Sketchfab official Download API"
    if zipfile.is_zipfile(archive):
        extracted = ORIGINAL / "Extracted"
        extracted.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                target = (extracted / member.filename).resolve()
                if not target.is_relative_to(extracted.resolve()):
                    raise SystemExit("Archive member escapes the extraction directory.")
            package.extractall(extracted)
        sources = [str(p.relative_to(ROOT)) for p in extracted.rglob("*") if p.suffix.lower() in (".gltf", ".glb", ".fbx", ".obj", ".blend")]
    else:
        sources = [str(archive.relative_to(ROOT))]
    digest = hashlib.sha256()
    with archive.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    receipt = {
        "model_uid": UID, "page": PAGE, "title": metadata.get("name"),
        "author": metadata.get("user", {}).get("displayName"), "license": metadata.get("license"),
        "archive": str(archive), "archive_bytes": archive.stat().st_size,
        "archive_sha256": digest.hexdigest(),
        "source_files": sources, "acquisition_method": method,
        "credential_saved": False, "temporary_url_saved": False,
        "source_acquired": True, "assets_imported": False, "runtime_tested": False,
    }
    save_json("acquisition_receipt.json", receipt)
    print(json.dumps({"source_acquired": True, "archive": str(archive), "sources": sources}))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        raise SystemExit("Official source request failed: HTTP " + str(error.code)) from None
    except urllib.error.URLError:
        raise SystemExit("Official source request failed; no credential or signed URL logged.") from None
