"""Bake geometry-derived skin/sleeve region fields into the existing UV atlas."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

OUT=Path(__file__).parent
N=4096
fields=np.zeros((N,N,2),np.float32)
valid=np.zeros((N,N),bool)
for face in json.loads((OUT/'forearm_faces.json').read_text()):
    pts=np.array([[u*(N-1),(1-v)*(N-1)] for u,v in face['uv']])
    a,b,c=pts
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-7: continue
    lo=np.maximum(0,np.floor(pts.min(axis=0)).astype(int))
    hi=np.minimum(N-1,np.ceil(pts.max(axis=0)).astype(int))
    if np.any(hi<lo): continue
    yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
    wc=1-wa-wb
    inside=(wa>=-.001)&(wb>=-.001)&(wc>=-.001)
    vals=np.array(face['fields'])[:,:2]
    interp=wa[...,None]*vals[0]+wb[...,None]*vals[1]+wc[...,None]*vals[2]
    patch=fields[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    patch[inside]=interp[inside]
    valid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=inside
dist,nearest=distance_transform_edt(~valid,return_indices=True)
edge=(~valid)&(dist<=4)
fields[edge]=fields[nearest[0][edge],nearest[1][edge]]
valid|=edge
t,inner=fields[...,0],fields[...,1]
def smooth(lo,hi,x):
    y=np.clip((x-lo)/(hi-lo),0,1)
    return y*y*(3-2*y)
skin=smooth(.31,.32,t)*valid
cuff=smooth(.245,.255,t)*(1-smooth(.305,.32,t))*valid
glove=np.asarray(Image.open(OUT/'T_Manny_GloveMask.png'),dtype=np.float32)/255
skin*=1-glove
cuff*=1-glove
rgba=np.stack((skin,np.clip(t,0,1)*valid,inner*valid,cuff),axis=-1)
Image.fromarray(np.uint8(np.clip(rgba*255,0,255))).save(OUT/'T_Manny_ForearmRegions.png')
assert not np.any((skin>.01)&(glove>.99))
(OUT/'regions_report.json').write_text(json.dumps({'channels':{'R':'exposed forearm skin','G':'elbow-to-wrist coordinate','B':'inner arm weighting','A':'fabric cuff band'},
    'skin_start_fraction':.31,'skin_full_fraction':.32,'skin_pixels':int(np.count_nonzero(skin>.5)),
    'glove_overlap_pixels':0,'mesh_modified':False},indent=2))
print('SKIN_REGIONS_PASS',int(np.count_nonzero(skin>.5)))
