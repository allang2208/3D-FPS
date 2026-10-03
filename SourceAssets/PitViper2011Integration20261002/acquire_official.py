"""Download one authorized Sketchfab model; credential comes from stdin only."""
import getpass, hashlib, json, sys, urllib.request, urllib.error, zipfile
from pathlib import Path

UID = "2daaf7fe78604ee7941a4ad5fd4d0153"
OUT = Path(__file__).resolve().parent
RAW = OUT / "Original"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.sketchfab.com/v3/models/" + UID

def get_json(url, auth=None):
    headers = {"User-Agent": "FPSGAME-AssetAcquisition/1.0"}
    if auth:
        headers["Authorization"] = auth
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
        return json.load(response)

print("Sketchfab credential input required; it will not be logged.", flush=True)
token = getpass.getpass("") if sys.stdin.isatty() else sys.stdin.readline().strip()
if not token:
    raise SystemExit("No credential supplied.")
try:
    metadata = get_json(API)
    if metadata.get("license", {}).get("slug") != "by":
        raise SystemExit("Model license differs from the requested CC BY source.")
    download = None
    for scheme in ("Token", "Bearer"):
        try:
            download = get_json(API + "/download", scheme + " " + token)
            break
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise
    token = None
    if not download:
        raise SystemExit("Sketchfab rejected the supplied credential (HTTP 401).")
    fmt = next((name for name in ("glb", "gltf") if download.get(name, {}).get("url")), None)
    if not fmt:
        raise SystemExit("No GLB/glTF archive returned by the official API.")
    item = download[fmt]
    archive = RAW / ("PitViper2011_Official.glb" if fmt == "glb" else "PitViper2011_Official.zip")
    # The temporary URL carries its own authorization. Never forward account credentials.
    req = urllib.request.Request(item["url"], headers={"User-Agent":"FPSGAME-AssetAcquisition/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, archive.open("wb") as dest:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            dest.write(chunk)
    metadata_path = OUT / "sketchfab_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    extracted = RAW / "Extracted"
    if zipfile.is_zipfile(archive):
        extracted.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                target = (extracted / member.filename).resolve()
                if not target.is_relative_to(extracted.resolve()):
                    raise SystemExit("Archive member is outside the extraction directory.")
            package.extractall(extracted)
        sources = [str(p.relative_to(OUT)) for p in extracted.rglob("*") if p.suffix.lower() in (".gltf", ".glb", ".fbx", ".obj", ".blend")]
    else:
        sources = [str(archive.relative_to(OUT))]
    receipt = {
        "model_uid":UID, "model_name":metadata["name"],
        "author":metadata.get("user", {}).get("displayName"),
        "license":metadata.get("license"), "official_archive":str(archive),
        "archive_bytes":archive.stat().st_size,
        "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
        "source_files":sources, "download_method":"Sketchfab official Download API",
        "credential_saved":False, "temporary_url_saved":False,
        "source_acquired":True, "assets_imported":False, "runtime_tested":False
    }
    (OUT / "acquisition_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2), encoding="utf-8")
    print(json.dumps({"source_acquired":True,"archive":str(archive),"bytes":archive.stat().st_size,"sources":sources}),flush=True)
except urllib.error.HTTPError as error:
    token = None
    raise SystemExit("Official download failed: HTTP " + str(error.code))
except urllib.error.URLError:
    token = None
    raise SystemExit("Official download network request failed; no credential or temporary URL logged.")
