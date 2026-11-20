"""Build the boot art bundle from one source revision under an artist export mutex."""
from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/RidgeBootsR2"
BLENDER = Path(os.getenv("BLENDER_EXE","E:/Program Files/Blender Foundation/Blender 5.1/blender.exe"))


def fingerprint():
    files = [ROOT/"Authored/boots_Jason.json",*sorted((ROOT/"Textures").glob("RB_*.png")),
             ROOT/"Reference/side.jpg",ROOT/"Reference/three_quarter.jpg",ROOT/"Reference/sole.jpg"]
    files.extend(HERE/name for name in ("ridge_boots_art.py","ridge_boots_art_photo.py","ridge_boots_art_render.py",
                                        "ridge_boots_art_sheet.py","ridge_boots_materials.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(2**20),b""):
                digest.update(chunk)
    return digest.hexdigest()


def blender(script,label,mode=None):
    cmd = [str(BLENDER),"-b","--factory-startup","-t","6","--python-exit-code","1","--python",str(HERE/script)]
    if mode:
        cmd.extend(("--",mode))
    log = ROOT/"Review"/(label+".log")
    with log.open("w",encoding="utf8") as stream:
        subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,check=True)


def main():
    from ridge_boots_art_sheet import comparison
    manifest = ROOT/"artwork.json"
    (ROOT/"Review").mkdir(parents=True,exist_ok=True)
    while True:
        start = fingerprint()
        if manifest.is_file() and json.loads(manifest.read_bytes()).get("fingerprint")==start:
            return
        blender("ridge_boots_art.py","artist-model")
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs=[pool.submit(blender,"ridge_boots_art_photo.py","photo-"+v,v) for v in ("icon","side","sole","quarter")]
            for job in jobs:
                job.result()
        comparison()
        if fingerprint()==start:
            break
    meta = json.loads((ROOT/"Models/models.json").read_bytes())
    meta.update(fingerprint=start, inventory_id="ue_modern_tactical_boots",
                standard_icon="Icons/ue_modern_tactical_boots.png",icon_pixels=[320,480],
                display="Icons/display.json",pickup="Icons/pickup.json",
                world_presentation="left and right boots upright and staggered, both outsoles at ground",
                reference_sheet="Review/reference-comparison.jpg",outsole_view="Review/outsole.png")
    manifest.write_text(json.dumps(meta,indent=2))
    print("RIDGE_BOOT_ART_READY", start, flush=True)


if __name__=="__main__":
    kernel = ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateMutexW.argtypes=(wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR)
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel.ReleaseMutex.argtypes=(wintypes.HANDLE,)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    gate=kernel.CreateMutexW(None,False,"Local\\FPSGAME-RidgeBootsR2-ArtistExport")
    if not gate:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(gate,0xffffffff) not in (0,0x80):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            main()
        finally:
            kernel.ReleaseMutex(gate)
    finally:
        kernel.CloseHandle(gate)
