"""Bake coat-family illustrations from the stable's actual Warhorse mesh and pigment atlas."""
from pathlib import Path
import json
import struct

import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
HORSES = ROOT / "SourceAssets/HillsVillageStable"
SOURCE = HORSES / "HorsesR7/Exchange"
COATS = [(52, 47, 44), (209, 205, 192), (143, 145, 143), (122, 77, 51)]
HAIR = [(45, 40, 37), (144, 139, 127), (83, 83, 80), (63, 45, 36)]
WIDTH, HEIGHT, AA = 384, 184, 2


def portrait_surface():
    glb = (SOURCE / "Warhorse_Stable.glb").read_bytes()
    size = struct.unpack_from("<I", glb, 12)[0]
    doc = json.loads(glb[20:20 + size])
    data = glb[28 + size:]
    prim = doc["meshes"][0]["primitives"][0]

    def read(index):
        item = doc["accessors"][index]
        view = doc["bufferViews"][item["bufferView"]]
        cols = {"VEC2": 2, "VEC3": 3, "SCALAR": 1}[item["type"]]
        dtype = np.dtype({5126: "<f4", 5123: "<u2", 5125: "<u4"}[item["componentType"]])
        return np.ndarray((item["count"], cols), dtype, data,
                          view.get("byteOffset", 0) + item.get("byteOffset", 0),
                          (view.get("byteStride", cols * dtype.itemsize), dtype.itemsize))

    attrs = prim["attributes"]
    pos, norm, uv = [read(attrs[k]) for k in ("POSITION", "NORMAL", "TEXCOORD_0")]
    eye = np.array([.86, .16, .49])
    eye /= np.linalg.norm(eye)
    right = np.cross([0, 1, 0], eye)
    right /= np.linalg.norm(right)
    up = np.cross(eye, right)
    origin = [0, 1.57, .60]
    scale = HEIGHT * AA / 1.39
    xy = np.column_stack(((pos-origin) @ right * scale + WIDTH*AA*.5,
                          HEIGHT*AA*.46 - (pos-origin) @ up * scale))
    depth = pos @ eye
    zbuf = np.full((HEIGHT*AA, WIDTH*AA), -np.inf)
    fields = np.zeros((*zbuf.shape, 5), np.float32)
    values = np.column_stack((uv, norm))
    for face in read(prim["indices"]).reshape(-1, 3):
        tri = xy[face]
        lo = np.maximum(np.floor(tri.min(0)).astype(int), 0)
        hi = np.minimum(np.ceil(tri.max(0)).astype(int), [WIDTH*AA-1, HEIGHT*AA-1])
        if (lo > hi).any():
            continue
        a, b = tri[1:] - tri[0]
        det = a[0]*b[1] - a[1]*b[0]
        if abs(det) < .001:
            continue
        bounds = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        yy, xx = np.ogrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        x, y = xx+.5-tri[0,0], yy+.5-tri[0,1]
        u, v = (x*b[1]-y*b[0])/det, (y*a[0]-x*a[1])/det
        z = depth[face]
        d = z[0]+u*(z[1]-z[0])+v*(z[2]-z[0])
        keep = (u >= 0) & (v >= 0) & (u+v <= 1) & (d > zbuf[bounds])
        zbuf[bounds][keep] = d[keep]
        p = values[face]
        fields[bounds][keep] = p[0]+u[keep,None]*(p[1]-p[0])+v[keep,None]*(p[2]-p[0])
    return fields[:,:,:2], fields[:,:,2:], np.isfinite(zbuf)


def sample(img, uv):
    return cv2.remap(img, (uv[:,:,0]*img.shape[1]-.5).astype("f"),
                     (uv[:,:,1]*img.shape[0]-.5).astype("f"), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


def main():
    uv, n, visible = portrait_surface()
    n /= np.maximum(.001, np.linalg.norm(n, axis=2, keepdims=True))
    maps = HORSES / "AppearanceR30"
    original = (sample(np.asarray(Image.open(SOURCE / "Warhorse_BaseColor.png").convert("RGB")), uv)/255)**2.2
    region = sample(np.asarray(Image.open(maps / "T_Warhorse_Regions.png")), uv)/255
    noise = np.asarray(Image.open(maps / "T_Warhorse_Pigment.png").convert("RGB"))
    luma = np.maximum(.0004, original @ [.25,.60,.15])
    coat_mask = np.clip((region[:,:,3:]-.51)/.49, 0, 1)
    hair_mask = np.clip((.49-region[:,:,3:])/.49, 0, 1)
    light = .68 + .96*np.maximum(0, n @ [.48,.77,.42]) + .44*np.maximum(0,n @ [-.69,.47,-.55])
    yy,xx = np.mgrid[:HEIGHT*AA,:WIDTH*AA]
    glow = np.clip(1-((xx/WIDTH/AA-.42)**2*1.45+(yy/HEIGHT/AA-.36)**2),0,1)
    # Give dark coats a lighter field for a readable ear, brow and muzzle silhouette.
    palettes = [([38,44,46],[74,78,75]),([30,32,32],[46,45,40]),
                ([39,37,34],[53,48,42]),([31,40,42],[54,65,64])]
    sheet = Image.new("RGB", (WIDTH*10, HEIGHT*4))
    soft_sheet = Image.new("RGB", (WIDTH*10//2, (HEIGHT//2)*4))
    for coat_id, coat_rgb in enumerate(COATS):
        shadow,lit_field = palettes[coat_id]
        backdrop = np.asarray(shadow)+glow[:,:,None]**2*np.asarray(lit_field)
        coat = (np.array(coat_rgb)/255)**2.2
        hair = (np.array(HAIR[coat_id])/255)**2.2
        variants = [(0,coat_id)] + [(pat,other) for pat in range(1,4) for other in range(4) if other!=coat_id]
        for col,(pattern, other) in enumerate(variants):
            x,y,z = (region[:,:,:3]*[100,220,260]*[.01,.0075,.021,.062][pattern]).transpose(2,0,1)
            a = np.stack((x+.44*y-.73*z, y+.51*z+.32*x),axis=2)*.55+[.23,.61]
            b = np.stack((z-.54*y+.36*x, x+.69*y+.22*z),axis=2)*.55+[.98,.60]
            field = (.61*sample(noise,a)[:,:,0]+.39*sample(noise,b)[:,:,1])/255
            t = np.clip((field-[1.25,.50,.61,.65][pattern])/[.05,.044,.064,.18][pattern]+.5,0,1)
            mix = (t*t*(3-2*t))[:,:,None]
            pigment = coat + mix*((np.array(COATS[other])/255)**2.2-coat)
            fur = pigment*np.clip((luma/.042)**.55,.26,1.7)[:,:,None]
            albedo = original+(fur-original)*coat_mask
            albedo += (hair*np.clip((luma/.035)**.65,.13,2.4)[:,:,None]-albedo)*hair_mask
            lit = 255*np.clip((albedo*light[:,:,None])**(1/2.2),0,1)
            plate = np.where(visible[:,:,None], lit, backdrop)
            plate = Image.fromarray(plate.astype("uint8")).resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
            sheet.paste(plate,(col*WIDTH,coat_id*HEIGHT))
            soft = plate.filter(ImageFilter.GaussianBlur(1.75)).resize((WIDTH//2,HEIGHT//2),Image.Resampling.LANCZOS)
            soft_sheet.paste(soft,(col*(WIDTH//2),coat_id*(HEIGHT//2)))
    path = ROOT / "Content/ColdSteelUI/HorseMarket/FieldPlates.jpg"
    path.parent.mkdir(exist_ok=True,parents=True)
    sheet.save(path, quality=94, subsampling=0)
    soft_sheet.save(path.with_name("FieldPlatesSoft.jpg"),quality=91,subsampling=0)


if __name__ == "__main__":
    main()
