"""Derive a tileable tangent normal from the accepted carbon height field."""
from pathlib import Path
from shutil import copyfile
from PIL import Image
import numpy as np
root=Path(__file__).resolve().parent
source=root.parent/'M24CarbonSpineConcept/ArtSource/woven_height.png'
copyfile(source,root/'Exports/T_CS_Weave_H.png')
copyfile(source.with_name('woven_face.png'),root/'Exports/T_CS_Weave_B.png')
h=np.asarray(Image.open(source).convert('L'),dtype=np.float32)/255.
slope=.085*.006
dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))*h.shape[1]*slope*.5
dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))*h.shape[0]*slope*.5
v=np.stack((-dx,-dy,np.ones_like(h)),axis=-1)
v/=np.linalg.norm(v,axis=-1,keepdims=True)
Image.fromarray(np.rint((v*.5+.5)*255).astype(np.uint8)).save(root/'Exports/T_CS_Weave_N.png')
