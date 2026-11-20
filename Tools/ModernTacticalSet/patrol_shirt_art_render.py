"""Produce published plates and both model masters from a matching garment revision."""
from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/PatrolShirtR2"
KEY = "ue_modern_kevlar_vest"
BLENDER = Path(os.getenv("BLENDER_EXE","E:/Program Files/Blender Foundation/Blender 5.1/blender.exe"))


def references():
    folder = ROOT/"Reference"
    data = json.loads((folder/"reference.json").read_bytes())
    views = {photo["role"]:folder/photo["filename"] for photo in data["photographs"]}
    return [views["front"],views["back"]]


def fingerprint():
    files = [ROOT/"World/shirt_Jason.json",*sorted((ROOT/"Textures").glob("PS_*.png")),*references(),
             ROOT.parent/"CombatShirtR4/Authored/vest_Jason.json",ROOT.parent/"ShoulderFit20261118/Jason-carrier.npz",
             ROOT.parent/"ShoulderFit20261118/Models/TS01_Vest_Jason.blend"]
    files.extend(HERE/name for name in ("patrol_shirt_art.py","patrol_shirt_art_photo.py","patrol_shirt_art_render.py",
                                        "patrol_shirt_materials.py","ridge_boots_art.py","field_pants_art.py"))
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.name.encode())
        with file.open("rb") as stream:
            for chunk in iter(lambda:stream.read(2**20),b""):
                digest.update(chunk)
    return digest.hexdigest()


def comparison():
    from PIL import Image, ImageDraw, ImageFont
    from field_pants_art_sheet import cut_photo
    review = ROOT/"Review"
    sheet = Image.new("RGB",(1240,1460),(243,241,236))
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",28)
    text = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",22)
    draw.text((35,22),"实物参考 · Helikon-Tex MCDU Combat Shirt",font=title,fill="#383328")
    draw.text((664,22),"游戏模型 · TS01 作战上衣",font=title,fill="#383328")
    for row,(ref,render,caption) in enumerate(zip(references(),("front.png","rear.png"),("正面","背面"))):
        top = 77+678*row
        for col,file in enumerate((ref,review/render)):
            x = 18+611*col
            draw.rectangle((x,top,x+590,top+666),fill=(255,255,255))
            draw.text((x+18,top+12),caption,font=text,fill="#655f53")
            im = cut_photo(file)
            scale = min(553/im.width,581/im.height)
            im = im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
            sheet.paste(im,(x+(590-im.width)//2,top+52+(581-im.height)//2),im)
    sheet.save(review/"reference-comparison.jpg",quality=94,optimize=True)


def blender(script,label,mode=None):
    cmd = [str(BLENDER),"-b","--factory-startup","-t","5","--python-exit-code","1","--python",str(HERE/script)]
    if mode:
        cmd.extend(("--",mode))
    with (ROOT/"Review"/(label+".log")).open("w",encoding="utf8") as stream:
        subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,check=True)


def build():
    (ROOT/"Review").mkdir(parents=True,exist_ok=True)
    manifest = ROOT/"artwork.json"
    while True:
        digest = fingerprint()
        if manifest.is_file() and json.loads(manifest.read_bytes())["fingerprint"]==digest:
            return
        blender("patrol_shirt_art.py","artist-model")
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(blender,"patrol_shirt_art_photo.py","photo-"+mode,mode)
                    for mode in ("front","rear","icon","pickup")]
            for job in jobs:
                job.result()
        comparison()
        if fingerprint()==digest:
            break
    meta = json.loads((ROOT/"Models/models.json").read_bytes())
    meta.update(inventory_id=KEY,fingerprint=digest,standard_icon="Icons/"+KEY+".png",icon_pixels=[480,480],
                display="Icons/display.json",pickup="Icons/pickup.json",
                world_presentation="original carrier front up, sleeves folded under and lower shirt hem folded back",
                reference_sheet="Review/reference-comparison.jpg")
    manifest.write_text(json.dumps(meta,indent=2),encoding="utf8")
    print("PATROL_SHIRT_ART_READY",digest,flush=True)


if __name__=="__main__":
    kernel = ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateMutexW.argtypes=(wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR)
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel.ReleaseMutex.argtypes=(wintypes.HANDLE,)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    gate = kernel.CreateMutexW(None,False,"Local\\FPSGAME-PatrolShirtR2-ArtistExport")
    if not gate:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(gate,0xffffffff) not in (0,0x80):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            build()
        finally:
            kernel.ReleaseMutex(gate)
    finally:
        kernel.CloseHandle(gate)
