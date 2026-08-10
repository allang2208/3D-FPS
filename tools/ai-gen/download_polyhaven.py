#!/usr/bin/env python3
"""Download Poly Haven (CC0) glTF models into assets/models/polyhaven/<name>.

Picks a resolution (default 2k, 1k for heavy geometry), downloads the .gltf,
.bin and every referenced texture, mirroring the layout of existing models:
  <name>/<name>_<res>.gltf
  <name>/<name>.bin
  <name>/textures/<map>_<res>.jpg

Usage:
  python tools/ai-gen/download_polyhaven.py searsia_burchellii shrub_01 ...
  --res 2k
"""

import argparse
import json
import os
import urllib.request

API = "https://api.polyhaven.com/files/{}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "models", "polyhaven"))


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.load(f)


def download(url, dest, expected=None):
    if os.path.exists(dest) and expected and abs(os.path.getsize(dest) - expected) < 2:
        print(f"  skip {os.path.basename(dest)} (exists)")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as f, open(dest, "wb") as out:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    print(f"  ok {os.path.basename(dest)} ({os.path.getsize(dest)//1024} KB)" if os.path.getsize(dest) > 1024 * 1024
          else f"  ok {os.path.basename(dest)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--res", default="2k")
    args = ap.parse_args()
    for name in args.names:
        data = fetch_json(API.format(name))
        variant = data["gltf"].get(args.res) or data["gltf"].get("1k")
        if not variant:
            print(f"{name}: no {args.res} variant, skip")
            continue
        g = variant["gltf"]
        dest_dir = os.path.join(ROOT, name)
        base = g["url"].rsplit("/", 1)[-1]  # e.g. searsia_burchellii_2k.gltf
        print(f"{name}: downloading {args.res} ({g['size']} bytes gltf)")
        download(g["url"], os.path.join(dest_dir, base), g["size"])
        for rel, meta in g.get("include", {}).items():
            # rel like "searsia_burchellii.bin" or "textures/xxx.jpg"
            rel = rel.replace("\\", "/")
            if rel.startswith("textures/"):
                dest = os.path.join(dest_dir, rel)
            else:
                dest = os.path.join(dest_dir, os.path.basename(rel))
            download(meta["url"], dest, meta.get("size"))


if __name__ == "__main__":
    main()
