"""Read the actual V7 skin and authored pull under the runtime crouch transform.
No rendering, asset writes or gameplay launch. This diagnoses the reported opening.
"""
import json, math, bmesh
from pathlib import Path
import numpy as np
from mathutils import Vector, Quaternion
P=Path(__file__).parent;ROOT=P.parents[1]
source=ROOT/'SourceAssets/BowFlex20260927/generated_actions.py'
scope={'__file__':str(source),'__name__':'bow_source'}
exec(compile(source.read_text(encoding='utf8').split('bpy.ops.wm.read_factory_settings')[0],str(source),'exec'),scope)
data=scope['data'];pose=scope['pose'];rest=scope['rest'];R=scope['R']
positions=np.array(data['positions']);base=positions@np.array(R).T
# Weld only a diagnostic topology copy so UV/material splits are not holes.
bm=bmesh.new()
for p in positions:bm.verts.new(p)
bm.verts.ensure_lookup_table()
for face in data['triangles']:
    try:bm.faces.new([bm.verts[i] for i in face])
    except ValueError:pass
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
edge_points={tuple(round(float(x),4) for x in v.co) for e in bm.edges if e.is_boundary for v in e.verts}
bm.free()
opening=[i for i,p in enumerate(positions) if tuple(round(float(x),4) for x in p) in edge_points
    and sum(w for b,w in data['weights'][i].items() if b.endswith('_l'))>.5]
upper=[i for i,w in enumerate(data['weights']) if sum(v for b,v in w.items() if b.endswith('_l') and ('upperarm' in b or 'clavicle' in b))>.5]
influences={}
for i,w in enumerate(data['weights']):
    for bone,value in w.items():influences.setdefault(bone,[]).append((i,value))
influences={bone:(np.array([i for i,w in rows]),np.array([w for i,w in rows])) for bone,rows in influences.items()}
skin_indices=np.array(sorted(set(opening+upper)))
cfg=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf8'))['bow_dark']
hip=Vector(tuple(float(x) for x in cfg['bow_hip_offset_cm'].split(',')))
offset=Vector(tuple(float(x) for x in cfg['bow_crouch_offset_cm'].split(',')))
arrow_rest=Vector(tuple(float(x) for x in cfg['arrow_rest_cm'].split(',')))
rows=[]
def framing(world,cant,offset):
    grip=world['bow_grip'].translation
    rotation=Quaternion((1,0,0),math.radians(cant))
    target_grip=grip+hip+offset
    tail=world['bow_nock'].translation;rest_point=world['bow_grip']@arrow_rest
    axis=rotation@((rest_point-tail).normalized());tail_from=rotation@(tail-grip)
    target_from=Vector((float(cfg['range_cm']),0,0))-target_grip
    along=tail_from.dot(axis)
    ray=tail_from+axis*(-along+math.sqrt(along*along+target_from.length_squared-tail_from.length_squared))
    rotation=ray.rotation_difference(target_from)@rotation
    return np.array(rotation.to_matrix()),np.array(target_grip-rotation@grip)
def visible(points,vertical_fov=75):
    slope=math.tan(math.radians(vertical_fov/2));x=points[:,0]
    return (x>1)&(np.abs(points[:,1])<x*slope*16/9)&(np.abs(points[:,2])<x*slope)
for q in (0.,.25,.5,.75,1.):
    world=pose('Draw',q*scope['DURATIONS']['Draw'])
    skin=np.zeros_like(base)
    for bone,(ids,weights) in influences.items():
        delta=np.array(world[bone]@rest[bone].inverted())
        skin[ids]+=(base[ids]@delta[:3,:3].T+delta[:3,3])*weights[:,None]
    for cant in (-55.,-30.,-20.,-12.,0.):
        rot,loc=framing(world,cant,offset)
        root=skin[opening]@rot.T+loc;arm=skin[upper]@rot.T+loc
        shoulder=rot@np.array(world['upperarm_l'].translation)+loc
        rows.append({'draw_phase':q,'cant':cant,'opening_vertices':len(opening),
            'opening_visible':int(visible(root).sum()),'upperarm_visible':int(visible(arm).sum()),
            'opening_min':root.min(axis=0).tolist(),'opening_max':root.max(axis=0).tolist(),
            'shoulder_cm':shoulder.tolist()})
(P/'framing-diagnosis.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for row in rows:print('CROUCH_DIAG',row['draw_phase'],row['cant'],'opening',row['opening_visible'],'upperarm',row['upperarm_visible'],'shoulder',row['shoulder_cm'])
