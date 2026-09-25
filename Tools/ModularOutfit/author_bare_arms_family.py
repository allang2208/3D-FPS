"""Transfer the accepted M4 V6 surface into each weapon's native reference pose.

No animation, weapon geometry, native skeleton or original mesh is changed.
Extra UV channels carry the accepted canonical skin coordinates for posed rigs.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=Path(globals().get('AUTHOR_ROOT',PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6'))
SOURCES=Path(globals().get('NATIVE_SOURCE_ROOT',ROOT/'Sources'))
BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
original=read(BASE/'M4_original.json')
refit=read(BASE/'RefinedSkinV3/hand_refit.json')
cut=read(BASE/'RefinedSkinV3/M4_original.json')
accepted=read(Path(globals().get('ACCEPTED_SHAPE',BASE/'BareUpperArmsV6/M4_original.json')))
source=read(SOURCES/'M4.json')
canonical=np.asarray(accepted['positions'],dtype=float)
base_positions=np.asarray(original['positions'],dtype=float)
distance,retained=cKDTree(refit['positions']).query(cut['positions'])
retained[distance>1e-5]=-1
if len(cut['positions'])!=len(canonical) or cut['triangles']!=accepted['triangles']:
    raise RuntimeError('Accepted shape no longer has the V3 cut topology; update authoring correspondence')
def bind(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
inverse={n:np.linalg.inv(bind(b)) for n,b in source['bones'].items()}
manifest=[]
config=read(PROJECT/'Content/ColdSteelData/modular_outfits.json')
for path,profile in config['profiles'].items():
    name=profile['rig_profile']
    if name=='Body' or (name=='M4' and not globals().get('INCLUDE_M4',False)):continue
    target=read(SOURCES/f'{name}.json')
    if target['source']!=path:raise RuntimeError('Source path changed during authoring: '+name)
    native=np.asarray(target['positions'],dtype=float)
    if len(native)==len(base_positions):
        if target['triangles']!=original['triangles'] or target['uv']!=original['uv']:
            raise RuntimeError('Native topology/UV correspondence changed: '+name)
        original_to_target={i:i for i in range(len(native))}
        keep=np.ones(len(canonical),dtype=bool)
    else:
        # Dual-wield assets contain one complete arm in the shared Manny rest pose.
        distance,index=cKDTree(base_positions).query(native)
        if max(distance)>.002:raise RuntimeError('Unrecognized single-arm reference pose: '+name)
        original_to_target={int(v):i for i,v in enumerate(index)}
        side=-1 if native[:,0].mean()<0 else 1
        keep=canonical[:,0]*side>0
    ids=np.flatnonzero(keep);remap={int(v):i for i,v in enumerate(ids)}
    matrices={n:bind(target['bones'][n])@inverse[n] for n in {n for w in accepted['weights'] for n in w}}
    positions=[];weights=[];linears=[]
    for vi in ids:
        oi=int(retained[vi]);ti=original_to_target.get(oi)
        w=target['weights'][ti] if ti is not None else accepted['weights'][vi]
        matrix=sum(matrices[n]*weight for n,weight in w.items())
        p=(matrix@np.append(canonical[vi],1))[:3]
        if ti is not None:
            # Preserve native contact positions, including sub-millimetre import rounding.
            p+=native[ti]-(matrix@np.append(base_positions[oi],1))[:3]
        positions.append(p.tolist());weights.append(w)
        linears.append(np.linalg.inv(matrix[:3,:3]).T)
    triangles=[];uv=[];normals=[];rest_normals=[];materials=[]
    for fi,face in enumerate(accepted['triangles']):
        if not all(keep[v] for v in face):continue
        row=[remap[v] for v in face];ns=[]
        for corner,vi in enumerate(row):
            n=linears[vi]@np.asarray(accepted['normals'][fi][corner]);n/=np.linalg.norm(n)
            ns.append(n.tolist())
        triangles.append(row);uv.append(accepted['uv'][fi]);normals.append(ns)
        rest_normals.append(accepted['normals'][fi]);materials.append(accepted['triangle_materials'][fi])
    data={'profile':name,'source':path,'skeleton':target['skeleton'],'source_sha256':target['source_sha256'],
          'positions':positions,'weights':weights,'triangles':triangles,'uv':uv,'normals':normals,
          'triangle_materials':materials,'canonical_positions':canonical[ids].tolist(),
          'canonical_normals':rest_normals,'surface_winding':'ue_native',
          'contract':'Accepted M4 V6 surface; native reference skeleton; original native grip weights; canonical skin field'}
    output=OUT/f'{name}.json';output.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    manifest.append({'profile':name,'source':path,'authored':str(output),'vertices':len(positions),'triangles':len(triangles)})
    print('BARE_FAMILY_AUTHORED',name,len(positions),len(triangles),flush=True)
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
