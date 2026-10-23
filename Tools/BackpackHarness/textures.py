"""Tileable woven olive fabric with continuous stitch rows; no atlas guessing."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

R=Path("D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020")
out=R/"Textures"
out.mkdir(parents=True,exist_ok=True)
n=1024
y,x=np.mgrid[0:n,0:n]/n
warp=.5+.5*np.sin(2*np.pi*x*128)
weft=.5+.5*np.sin(2*np.pi*y*128)
alternate=(np.floor(x*128)+np.floor(y*128))%2
weave=np.where(alternate==0,warp*.65+weft*.35,warp*.35+weft*.65)
stitch=np.zeros_like(x)
for band in (.065,.47,.565,.97):
    stitch=np.maximum(stitch,np.exp(-((x-band)/.0035)**2)*np.maximum(0,np.cos(2*np.pi*y*24))**.6)
height=weave*.08+stitch*.11
rgb=np.array([.235,.225,.145])[None,None,:]*(.90+.20*weave[:,:,None])
rgb+=stitch[:,:,None]*np.array([.075,.067,.040])
Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(out/"T_HarnessFabric_BaseColor.png")
orm=np.stack([np.ones_like(x),.86-.08*weave-.06*stitch,np.zeros_like(x)],axis=-1)
Image.fromarray(np.uint8(orm*255)).save(out/"T_HarnessFabric_ORM.png")
dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*2.0
dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*2.0
normal=np.stack([-dx,-dy,np.ones_like(x)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255)).save(out/"T_HarnessFabric_Normal_GL.png")
(out/"recipe.json").write_text(json.dumps({"size":1024,"v_repeat_cm":8,"normal":"OpenGL; flip green on UE import",
    "orm":"R=1 AO; G=roughness; B=0 metallic","base_color":"sRGB olive weave"},indent=2),encoding="utf-8")
print("HARNESS_FABRIC_TEXTURES_SAVED")
