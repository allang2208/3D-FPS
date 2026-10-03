"""Synchronize only the PKM outfit bindings to the current accepted native skin."""
import hashlib,json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925'
OUT=HERE/'Authored';OUT.mkdir(exist_ok=True)
BEFORE=HERE/'Before';BEFORE.mkdir(exist_ok=True)
raw=(ROOT/'BarePalmV7/Authored/PKM.json').read_bytes();bare=json.loads(raw)
native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())
P=[Vector(p) for p in bare['positions']]
report={}
for family in ('HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1'):
    source=ROOT/family/'Authored/PKM.json';original=source.read_bytes()
    backup=BEFORE/(family+'.json')
    if not backup.exists():backup.write_bytes(original)
    data=json.loads(original);changed=0
    if 'bare_vertex_ids' in data:
        for i,base_id in enumerate(data['bare_vertex_ids']):
            old=data['weights'][i];new=bare['weights'][base_id].copy()
            if sum(abs(old.get(n,0)-new.get(n,0)) for n in set(old)|set(new))>1.e-8:changed+=1
            data['weights'][i]=new
    else:
        for side in ('l','r'):
            e=Vector(native['bones']['lowerarm_'+side]['p']);w=Vector(native['bones']['hand_'+side]['p'])
            delta=w-e;length=delta.length;axis=delta.normalized()
            belongs=[sum(v for n,v in ws.items() if n.endswith('_'+side))>.99 for ws in bare['weights']]
            faces=[f for f in bare['triangles'] if all(belongs[i] for i in f)
                   and sum((P[i]-e).dot(axis)/length for i in f)/3<1.02]
            bvh=BVHTree.FromPolygons(P,faces,all_triangles=True)
            for vi,old in enumerate(data['weights']):
                if sum(v for n,v in old.items() if n.endswith('_'+side))<.99:continue
                point=Vector(data['positions'][vi]);station=(point-e).dot(axis)/length
                if station<=-.35:continue
                hit,_,fi,distance=bvh.find_nearest(point)
                f=faces[fi]
                bary=barycentric_transform(hit,*[P[i] for i in f],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
                target={}
                for bi,factor in zip(f,bary):
                    for n,value in bare['weights'][bi].items():target[n]=target.get(n,0)+max(0,float(factor))*value
                total=sum(target.values());target={n:v/total for n,v in target.items() if v>1.e-10}
                alpha=max(0,min(1,(station+.35)/.20));alpha=alpha*alpha*(3-2*alpha)
                new={n:old.get(n,0)*(1-alpha)+target.get(n,0)*alpha for n in set(old)|set(target)}
                total=sum(new.values());new={n:v/total for n,v in new.items() if v>1.e-9}
                if sum(abs(old.get(n,0)-new.get(n,0)) for n in set(old)|set(new))>1.e-8:changed+=1
                data['weights'][vi]=new
    data['bare_authored_sha256']=hashlib.sha256(raw).hexdigest()
    data['contract']+='; ArmJoint49 PKM: cuff and forearm weights synchronized to current V7 skin; geometry and contact surfaces retained'
    data['joint_revision']='ArmJoint49'
    (OUT/(family+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    report[family]={'source':str(source),'before_sha256':hashlib.sha256(original).hexdigest(),'vertices_rebound':changed}
    print('PKM_OUTFIT_AUTHORED',family,changed)
(HERE/'outfit_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
