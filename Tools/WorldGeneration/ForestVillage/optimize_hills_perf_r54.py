"""HillsPerfOpt-R54 headless UE5 texture optimization script.

Backs up original texture packages to Before/ with SHA-256 receipts,
caps oversized texture resolutions cleanly via MaxTextureSize (without altering
CompressionSettings so Material SamplerTypes stay 100% compatible), and writes
published.json in F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R54/.
"""

import hashlib
import json
import os
import shutil
import time
import unreal

PROJECT_CONTENT = r"D:\FPS3D\FPSGAME\Content"
OUT_DIR = r"F:\FPSGAMEData\ArtProduction\HillsForestPath\HillsPerfOpt-R54"
BEFORE_DIR = os.path.join(OUT_DIR, "Before")

TARGETS = [
    {
        "asset": "/Game/UndergroundTunnel/Textures/Effects/T_RainDrop01a",
        "kind": "raindrop_fx",
        "target_if_8k": 1024,
        "target_if_4k": 1024,
        "target_if_2k": 1024,
    },
    {
        "asset": "/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Body/Baked/T_Body_N",
        "kind": "character_body_normal",
        "target_if_8k": 4096,
        "target_if_4k": 2048,
        "target_if_2k": 0,
    },
    {
        "asset": "/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Body/Baked/T_Body_SRMF",
        "kind": "character_body_srmf",
        "target_if_8k": 4096,
        "target_if_4k": 2048,
        "target_if_2k": 0,
    },
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def asset_disk_files(object_path: str):
    pkg = object_path.split(".")[0]
    if not pkg.startswith("/Game/"):
        raise RuntimeError(f"Unsupported package path: {object_path}")
    rel = pkg[len("/Game/"):].replace("/", os.sep)
    base = os.path.join(PROJECT_CONTENT, rel)
    found = []
    for ext in (".uasset", ".uexp", ".ubulk"):
        p = base + ext
        if os.path.isfile(p):
            found.append((rel + ext, p))
    return found


def backup_files(files, label_dir):
    receipts = []
    for rel, src in files:
        dst = os.path.join(label_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.isfile(dst):
            shutil.copy2(src, dst)
        receipts.append({
            "rel_path": rel.replace("\\", "/"),
            "size_bytes": os.path.getsize(dst),
            "sha256": sha256_file(dst),
            "backup_path": dst.replace("\\", "/"),
        })
    return receipts


def read_tex_stats(tex: unreal.Texture2D):
    imp_x = int(tex.blueprint_get_size_x())
    imp_y = int(tex.blueprint_get_size_y())
    try:
        src_x = int(tex.get_editor_property("source").get_size_x()) if hasattr(tex, "get_editor_property") else imp_x
    except Exception:
        src_x = imp_x
    try:
        max_sz = int(tex.get_editor_property("max_texture_size"))
    except Exception:
        max_sz = 0
    try:
        comp = str(tex.get_editor_property("compression_settings"))
    except Exception:
        comp = "unknown"
    try:
        never_stream = bool(tex.get_editor_property("never_stream"))
    except Exception:
        never_stream = False
    try:
        lod_group = str(tex.get_editor_property("lod_group"))
    except Exception:
        lod_group = "unknown"
    try:
        mip_gen = str(tex.get_editor_property("mip_gen_settings"))
    except Exception:
        mip_gen = "unknown"
    return {
        "size_x": imp_x,
        "size_y": imp_y,
        "source_x": src_x,
        "max_texture_size": max_sz,
        "compression_settings": comp,
        "never_stream": never_stream,
        "lod_group": lod_group,
        "mip_gen_settings": mip_gen,
    }


def save_with_retry(eal, asset_obj, asset_path: str, max_wait_s: int = 180, interval_s: int = 5):
    deadline = time.time() + max_wait_s
    attempt = 0
    while True:
        attempt += 1
        if eal.save_loaded_asset(asset_obj, only_if_is_dirty=False):
            return True
        if time.time() >= deadline:
            raise RuntimeError(f"Failed to save asset after {max_wait_s}s ({attempt} attempts): {asset_path}")
        unreal.log(f"[R54-WAIT] save busy for {asset_path} (attempt {attempt}), retrying in {interval_s}s...")
        time.sleep(interval_s)


def main():
    os.makedirs(BEFORE_DIR, exist_ok=True)
    eal = unreal.EditorAssetLibrary
    results = []

    for item in TARGETS:
        asset_path = item["asset"]
        tex = unreal.load_asset(asset_path)
        if not tex or not isinstance(tex, unreal.Texture2D):
            raise RuntimeError(f"Failed to load Texture2D: {asset_path}")

        before_stats = read_tex_stats(tex)
        unreal.log(
            f"[R54-INSPECT] {asset_path} | {before_stats['size_x']}x{before_stats['size_y']} "
            f"max={before_stats['max_texture_size']} comp={before_stats['compression_settings']} "
            f"never_stream={before_stats['never_stream']} lod_group={before_stats['lod_group']} mip_gen={before_stats['mip_gen_settings']}"
        )
        files = asset_disk_files(asset_path)
        before_files = backup_files(files, BEFORE_DIR)

        cur_dim = max(before_stats["size_x"], before_stats["size_y"])
        target_cap = 0
        if cur_dim >= 8192 and item["target_if_8k"] > 0:
            target_cap = item["target_if_8k"]
        elif cur_dim >= 4096 and item["target_if_4k"] > 0:
            target_cap = item["target_if_4k"]
        elif cur_dim >= 2048 and item["target_if_2k"] > 0:
            target_cap = item["target_if_2k"]

        changed = False
        if target_cap > 0 and (before_stats["max_texture_size"] == 0 or before_stats["max_texture_size"] > target_cap):
            tex.modify()
            tex.set_editor_property("max_texture_size", int(target_cap))
            save_with_retry(eal, tex, asset_path, max_wait_s=180, interval_s=5)
            changed = True

        after_stats = read_tex_stats(tex)
        after_files = []
        for rel, src in asset_disk_files(asset_path):
            after_files.append({
                "rel_path": rel.replace("\\", "/"),
                "size_bytes": os.path.getsize(src),
                "sha256": sha256_file(src),
            })

        entry = {
            "asset": asset_path,
            "kind": item["kind"],
            "requested_cap": target_cap,
            "changed": changed,
            "before": before_stats,
            "after": after_stats,
            "before_files": before_files,
            "after_files": after_files,
        }
        results.append(entry)
        unreal.log(
            f"[R54-TEX] {asset_path} | before={before_stats['size_x']}x{before_stats['size_y']} "
            f"(max={before_stats['max_texture_size']}, comp={before_stats['compression_settings']}, "
            f"never_stream={before_stats['never_stream']}) -> "
            f"after={after_stats['size_x']}x{after_stats['size_y']} (max={after_stats['max_texture_size']}) "
            f"changed={changed}"
        )

    receipt = {
        "batch": "HillsPerfOpt-R54",
        "before_dir": BEFORE_DIR.replace("\\", "/"),
        "targets": results,
    }
    receipt_path = os.path.join(OUT_DIR, "published.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    unreal.log(f"[R54-DONE] wrote {receipt_path}")


if __name__ == "__main__":
    main()
