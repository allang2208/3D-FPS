"""Publish the four generated factory icon masters to the PNG-consuming workbench."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish():
    masters = HERE / "Masters"
    masters.mkdir(exist_ok=True)
    # The generated files are bootstrap inputs only. Subsequent publication uses
    # the durable project masters, even after Codex-generated previews are gone.
    for row in MANIFEST["assets"]:
        master = HERE / row["master"]
        if not master.is_file():
            shutil.copy2(row["generated_file"], master)

    pending = []
    for row in MANIFEST["assets"]:
        master = HERE / row["master"]
        image_header = master.read_bytes()[:24]
        width, height = struct.unpack(">II", image_header[16:24])
        master_hash = digest(master)
        for relative in row["targets"]:
            target = ROOT / relative
            if target.is_file() and digest(target) == master_hash:
                continue
            backup = HERE / "Before" / relative
            if target.is_file() and not backup.is_file():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            pending.append({
                "slot": row["slot"],
                "source": master.relative_to(ROOT).as_posix(),
                "target": relative,
                "previous_sha256": digest(target) if target.is_file() else None,
                "backup": backup.relative_to(ROOT).as_posix() if backup.is_file() else None,
                "sha256": master_hash,
                "dimensions": [width, height],
            })

    for entry in pending:
        target = ROOT / entry["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / entry["source"], target)

    receipts = HERE / "Receipts"
    receipts.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    receipt = {
        "created_utc": now.isoformat(),
        "generator": "built-in image_gen",
        "changed_files": pending,
        "runtime_png_count": sum(row["target"].startswith("Content/") for row in pending),
        "texture_assets": "No Texture2D mirror is consumed for these factory icons; UI reads PNG directly.",
        "native_build": "not required; no runtime source change",
        "runtime_tested": False,
        "unchanged": ["whole-weapon inventory icon", "no-rune icon", "fixed neck/shaft icons", "shared accessories"],
    }
    receipt_path = receipts / (now.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(receipt_path), "changed_files": len(pending),
                      "runtime_png_count": receipt["runtime_png_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    publish()
