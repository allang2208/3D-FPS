"""Build real triangle-contact fields for offline harness and carrier fitting."""
import json,os
from pathlib import Path
import numpy as np
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactFitR3'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');records=read(R/'captured.json');out=R/'Surfaces';out.mkdir(exist_ok=True)
rot=lambda q:np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
male={b['name']:b for b in records[plan['rigs']['Jason']['body']]['bones']};frames={};index={}
xs=np.arange(-30.,30.01,.5);zs=np.arange(84.,168.01,.5);angles=np.arange(128)*2*np.pi/128;polar_z=np.arange(88.,154.01,.5)
for rig,inputs in plan['rigs'].items():
    bones={b['name']:b for b in records[inputs['body']]['bones']};target=bones['spine_04'];source=male['spine_04']
    matrix=rot(source['rotation'])@rot(target['rotation']).T;translation=np.asarray(target['position'])-np.asarray(source['position'])@matrix
    norm=lambda v:(v-translation)@matrix.T
    shoulder=norm(np.asarray(bones['clavicle_l']['position']));shoulder_shift=float(shoulder[2]-male['clavicle_l']['position'][2])
    frames[rig]={'matrix':matrix.tolist(),'translation':translation.tolist(),'shoulder_shift':shoulder_shift}
    def bvh(path):
        folder=Path(records[path]['folder']);v=norm(np.fromfile(folder/'positions.bin',dtype='<f4').reshape(-1,3));f=np.fromfile(folder/'triangles.bin',dtype='<i4').reshape(-1,3)
        return BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
    body=bvh(inputs['body']);head=bvh(inputs['head']) if inputs.get('head') else None;pants=[bvh(p) for p in inputs['pants']]
    body_rear=np.full((len(xs),len(zs)),np.nan);waist=np.full_like(body_rear,np.nan)
    for i,x in enumerate(xs):
        for j,z in enumerate(zs):
            origin=Vector((x,-100,z));direction=Vector((0,1,0));hit=body.ray_cast(origin,direction,200)[0]
            if hit is not None:body_rear[i,j]=hit.y
            if head:
                hit=head.ray_cast(origin,direction,200)[0]
                if hit is not None:body_rear[i,j]=np.fmin(body_rear[i,j],hit.y)
            if z<111:
                hits=[t.ray_cast(origin,direction,200)[0] for t in pants];hits=[h.y for h in hits if h is not None]
                if hits:waist[i,j]=min(hits)
    spine=np.asarray(sorted([norm(np.asarray(b['position'])).tolist() for n,b in bones.items() if n=='pelvis' or n.startswith('spine_')],key=lambda v:v[2]))
    centers=np.column_stack([np.interp(polar_z,spine[:,2],spine[:,axis]) for axis in [0,1]])
    for shirt,path in {'':None,**inputs['shirts']}.items():
        garments=[bvh(p) for p in inputs.get('shirt_surfaces',{}).get(shirt,[path] if path else [])];rear=body_rear.copy()
        for garment in garments:
            for i,x in enumerate(xs):
                for j,z in enumerate(zs):
                    hit=garment.ray_cast(Vector((x,-100,z)),Vector((0,1,0)),200)[0]
                    if hit is not None:rear[i,j]=np.fmin(rear[i,j],hit.y)
        guarded=np.fmin(rear,waist)
        radius=np.full((len(polar_z),len(angles)),np.nan)
        for zi,z in enumerate(polar_z):
            origin=Vector((centers[zi,0],centers[zi,1],z))
            for ai,a in enumerate(angles):
                direction=Vector((np.cos(a),np.sin(a),0));hits=[]
                for tree in [body]+garments:
                    hit=tree.ray_cast(origin,direction,40.)
                    if hit[0] is not None:hits.append(hit[3])
                if hits:radius[zi,ai]=max(hits)
        key=rig+'_'+(shirt or 'bare');file=out/(key+'.npz')
        np.savez_compressed(file,xs=xs,zs=zs,rear=rear,guarded_rear=guarded,polar_z=polar_z,angles=angles,radius=radius,centers=centers)
        index[key]=str(file);print('BACKPACK_SURFACE',key,flush=True)
(out/'frames.json').write_text(json.dumps(frames,indent=2));(out/'index.json').write_text(json.dumps(index,indent=2))
print('BACKPACK_SURFACES_COMPLETE',len(index),flush=True)
