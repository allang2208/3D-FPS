"""Fit every sewn carrier layer to the same measured female body envelope."""
import ast,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from smooth_vest_frame import positions
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'Integration'
sys.path.insert(0,str(S))
from carrier_surface import CarrierSurface
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
male=read(R/'Delivery/vest_Jason_Wear.json');path=R/'Delivery/vest_Kaitlin_Wear.json';d=read(path)
ms=CarrierSurface(read(P/'SourceAssets/JasonPlayer20261003/Jason.json'))
fs=CarrierSurface(read(P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/MHC_Kaitlin_Body.json'),None)
def frame(p):return np.asarray(positions(dict(positions=np.asarray(p).tolist(),bones=male['bones']),d['bones']))
src=np.asarray(male['positions']);p=frame(src);original=p.copy()
for side in [-1,1]:
    mask=(src[:,1]-1.5)*side>=0
    ids=np.flatnonzero(mask);sp=src[mask];tp=p[mask]
    base=np.array([ms.carrier(q[0],q[2],side,1.7) for q in sp]);mapped=frame(base)
    target=np.array([fs.carrier(q[0],q[2],side,1.7) for q in tp])
    example=int(np.argmax(abs(target[:,1]-mapped[:,1])))
    print('ENVELOPE_EXTREME',side,'source',sp[example].tolist(),'source_base',base[example].tolist(),'mapped_base',mapped[example].tolist(),'target_base',target[example].tolist(),flush=True)
    blend=np.clip(abs(sp[:,1]-1.5)/4,0,1)*np.clip((147-sp[:,2])/7,0,1)
    p[ids,1]+=(target[:,1]-mapped[:,1])*blend
# Preserve each shoulder layer's radial space over the actual native body.
# Open section edges do not supply a reliable nearest-face inside sign.
for i,q in enumerate(src):
    if q[2]<=141 or not 6<abs(q[0])<19:continue
    center=np.array([q[0],1.5,138.5]);v=q-center;radius=np.linalg.norm(v);direction=v/radius
    hit=ms.tree.ray_cast(Vector(center+direction*35),Vector(-direction),35)[0]
    if hit is None:continue
    clearance=max(.35,radius-np.linalg.norm(np.asarray(hit)-center))
    target_center=frame([center])[0];target_vec=original[i]-target_center;target_dir=target_vec/np.linalg.norm(target_vec)
    th=fs.tree.ray_cast(Vector(target_center+target_dir*35),Vector(-target_dir),35)[0]
    if th is None:continue
    out=target_center+target_dir*(np.linalg.norm(np.asarray(th)-target_center)+clearance)
    blend=float(np.clip((q[2]-141)/6,0,1));p[i]=(1-blend)*p[i]+blend*out
faces=np.asarray(d['triangles']);slots=d['material_slots']
# The two quick-release assemblies are rigid hardware, not stretch cloth.
hardware=np.unique(faces[np.asarray(d['triangle_materials'])==slots.index('TS01_MattePolymer')])
for sign in [-1,1]:
    ids=hardware[src[hardware,0]*sign>0];a=src[ids];b=p[ids];ac=a.mean(0);bc=b.mean(0)
    u,_,vh=np.linalg.svd((a-ac).T@(b-bc));rotation=u@vh
    if np.linalg.det(rotation)<0:u[:,-1]*=-1;rotation=u@vh
    p[ids]=(a-ac)@rotation+bc
d['positions']=p.tolist();d['normals']=male['normals']
tree=ast.parse((P/'Tools/ModernTacticalSet/derive.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transport_normals'],type_ignores=[]),'ts01_normals','exec'))
transport_normals(d,src)
# Transport preserves authored sharp boundaries. Average within each original
# smooth corner group so triangle-wise rotations do not facet the cloth.
original_normals=np.asarray(male['normals']).reshape(-1,3)
keys=np.column_stack([faces.reshape(-1),np.round(original_normals,4)])
_,inverse=np.unique(keys,axis=0,return_inverse=True)
normals=np.asarray(d['normals']).reshape(-1,3)
accum=np.zeros((int(inverse.max())+1,3));np.add.at(accum,inverse,normals)
accum/=np.maximum(np.linalg.norm(accum,axis=1,keepdims=True),1e-12)
d['normals']=accum[inverse].reshape(-1,3,3).tolist()
path.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
report=dict(method='Common measured front/back envelopes and radial shoulder clearance; native female binding',max_frame_delta_cm=float(np.linalg.norm(p-original,axis=1).max()))
(R/'QualityR3/female-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TS01_FEMALE_CLEARANCE',report,flush=True)
