"""Refresh the products from the same cut if the authored native mesh has changed."""
from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/FieldTrousersR2"
BLENDER=Path(os.getenv("BLENDER_EXE","E:/Program Files/Blender Foundation/Blender 5.1/blender.exe"))


def blender(script,name,arguments=()):
    log=ROOT/"Review"/(name+".log")
    with log.open("w",encoding="utf8") as stream:
        subprocess.run([str(BLENDER),"-b","--factory-startup","-t","5","--python-exit-code","1",
            "--python",str(HERE/script),*arguments],stdout=stream,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,check=True)


def main():
    digest=hashlib.sha256((ROOT/"Authored/pants_Jason.json").read_bytes()).hexdigest()
    manifest=ROOT/"artwork.json"
    if manifest.is_file() and json.loads(manifest.read_bytes())["source_sha256"]==digest:return
    (ROOT/"Review").mkdir(parents=True,exist_ok=True)
    blender("field_pants_art.py","artist-model")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(blender,"field_pants_art_photo.py","photo-"+k,("--",k)) for k in ("icon","front","rear","side")]
        for job in futures:job.result()
    from field_pants_art_sheet import main as comparison
    comparison()


if __name__=="__main__":
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateMutexW.argtypes=(wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR)
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel.ReleaseMutex.argtypes=(wintypes.HANDLE,)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    gate=kernel.CreateMutexW(None,False,"Local\\FPSGAME-FieldTrousersR2-ArtistExport")
    if not gate:raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(gate,0xffffffff) not in (0,0x80):
            raise ctypes.WinError(ctypes.get_last_error())
        try:main()
        finally:kernel.ReleaseMutex(gate)
    finally:kernel.CloseHandle(gate)
