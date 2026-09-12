"""Bake a local G8 cuff field and physically oriented tangent normal for a thin hem."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

OUT=Path(__file__).parent
N=4096
LENGTH=.27251
START=1-.03/LENGTH
MIN_T=START-.005
SPAN=.045
geometry=json.loads((OUT/'geometry_report.json').read_text())
axes={k:(np.array(v['wrist'])-np.array(v['elbow']))/v['length_m'] for k,v in geometry['axes'].items()}
field=np.zeros((N,N),np.uint8)
normal=np.empty((N,N,3),np.uint8);normal[:]=[128,128,255]
valid=np.zeros((N,N),bool)
faces=json.loads((OUT/'forearm_faces.json').read_text())

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)

for face in faces:
    uv=np.array(face['uv']);data=np.array(face['fields'])
    pts=uv*np.array([N-1,-(N-1)])+np.array([0,N-1])
    a,b,c=pts
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-7:continue
    lo=np.maximum(0,np.floor(pts.min(axis=0)).astype(int));hi=np.minimum(N-1,np.ceil(pts.max(axis=0)).astype(int))
    if np.any(hi<lo):continue
    yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
    wc=1-wa-wb;inside=(wa>=-.001)&(wb>=-.001)&(wc>=-.001)
    weights=np.stack([wa[inside],wb[inside],wc[inside]],axis=-1)
    t=weights@data[:,0]
    ns=unit(weights@data[:,5:8])
    p=data[:,2:5];e1=p[1]-p[0];e2=p[2]-p[0]
    du1=uv[1]-uv[0];du2=uv[2]-uv[0]
    determinant=du1[0]*du2[1]-du1[1]*du2[0]
    if abs(determinant)<1e-12:continue
    dpdu=(e1*du2[1]-e2*du1[1])/determinant
    dpdv=(-e1*du2[0]+e2*du1[0])/determinant
    tangent=unit(dpdu-ns*np.sum(ns*dpdu,axis=-1,keepdims=True))
    bitangent=np.cross(ns,tangent)
    handedness=np.where(np.sum(bitangent*dpdv,axis=-1,keepdims=True)>=0,1,-1)
    bitangent*=handedness
    axis=axes['l' if p[:,0].mean()<0 else 'r']
    d=(t-START)*LENGTH
    # A 0.65 mm rounded fold centred 2.2 mm inside the leather opening,
    # followed by a shallow 0.10 mm seam groove at 4.8 mm.
    ridge=.00065*np.exp(-((d-.0022)/.0012)**2)
    groove=-.00010*np.exp(-((d-.0048)/.00042)**2)
    slope=-2*(d-.0022)/(.0012**2)*ridge-2*(d-.0048)/(.00042**2)*groove
    surface_axis=axis-ns*np.sum(ns*axis,axis=-1,keepdims=True)
    bent=unit(ns-slope[:,None]*surface_axis)
    # DirectX texture convention: invert the UV-up bitangent component.
    tangent_normal=np.stack([np.sum(bent*tangent,axis=-1),-np.sum(bent*bitangent,axis=-1),np.sum(bent*ns,axis=-1)],axis=-1)
    region=np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    field[region][inside]=np.uint8(np.rint(np.clip((t-MIN_T)/SPAN,0,1)*255))
    normal[region][inside]=np.uint8(np.rint(np.clip(tangent_normal*.5+.5,0,1)*255))
    valid[region]|=inside

dist,nearest=distance_transform_edt(~valid,return_indices=True)
edge=(~valid)&(dist<=4)
field[edge]=field[nearest[0][edge],nearest[1][edge]]
normal[edge]=normal[nearest[0][edge],nearest[1][edge]]
Image.fromarray(field).save(OUT/'T_Manny_Cuff3cmField.png')
Image.fromarray(normal).save(OUT/'T_Manny_Cuff3cmRollNormal.png')
(OUT/'edge_report.json').write_text(json.dumps({'extension_cm':3,'start_fraction':START,'field_min_t':MIN_T,'field_span':SPAN,
    'fold_width_mm':4,'normal_height_mm':.65,'groove_depth_mm':.1,'normal_convention':'DirectX','mesh_modified':False,
    'method':'Surface-relative rolled-edge normal, local distance mask, and subtle contact tone'},indent=2))
print('CUFF_3CM_EDGE_BAKE_PASS')
