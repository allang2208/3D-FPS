"""Author high-boot skin coverage and tucked trouser variants in native space."""
import json
import copy
from pathlib import Path
import numpy as np

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArmoredBoots20261004'
def read(name):return json.loads((R/(name+'.json')).read_text())
def write(name,data):(R/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')

base=read('base');positions=np.array(base['positions']);tri=np.array(base['triangles'],int);mid=positions[tri].mean(1)
old=np.array(base['triangle_materials']);covered=(mid[:,2]<36.6)&(np.abs(mid[:,0])>3)
materials=copy.deepcopy(base['materials']);regions=old.copy();origins={};covers=[]
for original in sorted(set(old[covered].tolist())):
    matching=old==original
    if np.all(covered[matching]):covers.append(original);continue
    section=len(materials);origins[str(section)]=original
    materials.append(dict(slot='SkinArmoredBoot_'+str(original),asset=materials[original]['asset']))
    regions[matching&covered]=section;covers.append(section)
base.update(triangle_materials=regions.tolist(),materials=materials,section_origins=origins,armored_boot_covers=covers)
write('base_fitted',base)

def tucked(points):
    out=np.array(points,float).copy();z=out[:,2]
    levels=[4,8,12,18,24,30,36,40]
    cx=np.interp(z,levels,[14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1])
    cy=np.interp(z,levels,[-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5])
    rx=np.interp(z,levels,[4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35])-.64
    ry=np.interp(z,levels,[5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85])-.64
    sign=np.where(out[:,0]>=0,1.,-1.);dx=out[:,0]-sign*cx;dy=out[:,1]-cy
    radius=np.sqrt((dx/rx)**2+(dy/ry)**2);scale=np.minimum(1,1/np.maximum(radius,1e-8))
    t=np.clip((43-z)/5,0,1);t=t*t*(3-2*t);scale=1+(scale-1)*t
    out[:,0]=sign*cx+dx*scale;out[:,1]=cy+dy*scale
    return out

for key in ['jeans','cargo']:
    data=read(key);data['positions']=tucked(data['positions']).tolist();write(key+'_fitted',data)

data=json.loads((P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/Jason_ChainmailPants.json').read_text())
original=np.array(data['positions']);result=original.copy();cloth=np.zeros(len(original),bool)
for part in data['parts']:
    if part['name'].startswith(('Mail_Leg','Lining_Ankle','HemBinding')):
        start=part['first_vertex'];cloth[start:start+part['vertices']]=True
result[cloth]=tucked(original[cloth]);data['positions']=result.tolist()
# Transform existing cloth corner normals by the local deformation gradient;
# all accepted metal parts and their custom normals remain byte-for-byte values.
indices=np.flatnonzero(cloth);points=original[indices];eps=.002;jac=np.empty((len(points),3,3))
for axis in range(3):
    delta=np.zeros(3);delta[axis]=eps
    jac[:,:,axis]=(tucked(points+delta)-tucked(points-delta))/(2*eps)
# Radial compression can flatten saturated cross sections; bounded pseudo-inverse
# supplies the proper normal transform without introducing singular UVs.
normal_map=np.transpose(np.linalg.pinv(jac,rcond=1e-5),(0,2,1));lookup={vi:j for j,vi in enumerate(indices)}
for fi,face in enumerate(data['triangles']):
    for ci,vi in enumerate(face):
        if vi not in lookup:continue
        n=normal_map[lookup[vi]]@np.array(data['normals'][fi][ci]);length=np.linalg.norm(n)
        if length>1e-9:data['normals'][fi][ci]=(n/length).tolist()
data['contract']+='; ArmoredBoots tucked cloth variant, original armor and native weights retained'
write('Jason_ChainmailPants_ArmoredBootsFit',data)
write('fit_receipt',dict(coverage_height_cm=36.6,section_origins=origins,covers=covers,
    trousers=['ue_jeans','ue_cargo_pants','ue_chainmail_pants'],cloth_blend_height_cm=[38,43],runtime_tested=False))
print('ARMORED_BOOT_COMPANIONS_AUTHORED',covers,flush=True)
