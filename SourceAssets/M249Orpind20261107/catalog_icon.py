"""Rasterize the actual M249 art for the inventory and reuse the established bipod frame."""
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/"Content/ColdSteelData"
FRAMES=OUT/"AttachmentIcons20260913/FramedFirearms"
def render(groups,size,fold):
    texture=np.asarray(Image.open(ROOT/"Textures/T_M249_Color.png").convert("RGB").resize((1024,1024)))
    points=[];colors=[];depths=[]
    eye=np.array([.13,-.99,.18]);eye/=np.linalg.norm(eye)
    screen_x=np.cross(eye,[0,0,1]);screen_x/=np.linalg.norm(screen_x)
    screen_y=np.cross(screen_x,eye)
    for group in groups:
        j=np.load(group);p=j["positions"].astype(float);n=j["normals"].astype(float);f=j["faces"]
        if fold and group.stem in ("LegLeft","LegRight"):
            anchor=p[p[:,2]>p[:,2].max()-.009].mean(0);foot=p[p[:,2]<p[:,2].min()+.011].mean(0)
            vr=foot-anchor;vr/=np.linalg.norm(vr);target=np.array([1,.08 if group.stem=="LegRight" else -.08,-.11]);target/=np.linalg.norm(target)
            rot,_=Rotation.align_vectors([target],[vr]);p=rot.apply(p-anchor)+anchor;n=rot.apply(n)
        coords=j["uv"][f].mean(1)%1
        albedo=texture[(coords[:,1]*1023).astype(int),(coords[:,0]*1023).astype(int),:].astype(float)
        normal=n[f].mean(1);diffuse=np.clip(normal@np.array([-.25,-.55,.8]),-.3,1)
        # A neutral studio fill lifts the worn dark metal off a transparent slot.
        color=np.clip((albedo*.86+20)*(1.03+.47*diffuse[:,None]),0,255).astype(np.uint8)
        points.append(np.stack([p@screen_x,-p@screen_y],axis=-1)[f]);colors.append(color);depths.append((p@eye)[f].mean(1))
    pts=np.concatenate(points);colors=np.vstack(colors);sort=np.argsort(np.concatenate(depths))
    lo,hi=pts.min((0,1)),pts.max((0,1));width,height=size
    scale=min(width*.94/(hi-lo)[0],height*.9/(hi-lo)[1])
    pts=np.round((pts-(lo+hi)/2)*scale+[width/2,height/2]).astype(int)
    im=Image.new("RGBA",size);draw=ImageDraw.Draw(im)
    for i in sort:
        draw.polygon([tuple(p) for p in pts[i]],fill=tuple(colors[i])+(255,))
    return im
files=sorted((ROOT/"Geometry").glob("*.npz"))
# Inventory artwork follows the current UE model, mounted factory parts and
# the same horizontal orthographic studio as the live inventory thumbnail.
# Keep the legacy rasterizer below only for the existing bipod frame artwork.
inventory_author=ROOT.parents[1]/"SourceAssets/InventoryWeaponIcons20261108"
subprocess.run(["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "-NoProfile","-ExecutionPolicy","Bypass","-File",
                str(inventory_author/"produce_m249.ps1")],check=True)
shutil.copy2(inventory_author/"Artwork/ue_m249.png",OUT/"Icons/ue_m249.png")
# Reuse the project's common removal art and outer riveted grey plate.
base=Image.open(FRAMES/"ue_lmg201_bipod_lmg201_no_bipod.png").convert("RGBA")
w,h=base.size
draw=ImageDraw.Draw(base)
for radius in range(int(.341*w),0,-1):
    k=radius/(.341*w);v=int(41-16*k*k)
    draw.ellipse((w/2-radius,h/2-radius,w/2+radius,h/2+radius),fill=(v,v,v,255))
bipod=render([f for f in files if f.stem in ("LegLeft","LegRight","BipodMount")],(800,800),False)
bipod=bipod.crop(bipod.getbbox())
bipod.thumbnail((int(w*.60),int(h*.58)),Image.Resampling.LANCZOS)
gray=ImageOps.grayscale(bipod).point(lambda x:min(255,int(x*1.35+24)))
neutral=Image.merge("RGBA",(gray,gray,gray,bipod.getchannel("A")))
base.alpha_composite(neutral,((w-neutral.width)//2,(h-neutral.height)//2))
base.save(FRAMES/"ue_m249_bipod_false.png")
base.save(FRAMES/"ue_m249_category_bipod.png")
shutil.copyfile(FRAMES/"ue_lmg201_bipod_lmg201_no_bipod.png",FRAMES/"ue_m249_bipod_m249_no_bipod.png")
