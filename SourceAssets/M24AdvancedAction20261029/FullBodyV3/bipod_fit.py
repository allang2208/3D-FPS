"""User-requested mount-gap diagnosis in the shared authoring frame (metres)."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;S=O.parents[1]
def tree(objects):
    vs=[];fs=[]
    for ob in objects:
        off=len(vs);vs.extend([ob.matrix_world@v.co for v in ob.data.vertices])
        fs.extend([tuple(off+i for i in p.vertices) for p in ob.data.polygons])
    return BVHTree.FromPolygons(vs,fs)
def load(path,names):
    bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
    return tree([o for o in bpy.data.objects if o.type=='MESH' and names(o.name)])
native=load(S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend',lambda n:n=='M24_base')
old=load(S/'M24Bipod20261029/M24_Bipod_Editable.blend',lambda n:n.startswith('M24Bipod_Base_'))
body=load(O/'M24_AdvancedAction_FullBodyV3.blend',lambda n:n=='M24_AdvancedAction_DetailBody')
base=load(O/'M24_AdvancedAction_BipodSeatV3.blend',lambda n:n=='M24_Bipod_SeatV3')
samples=[]
for y in (.435,.45,.465):
    for x in (-.01,0,.01):
        row=dict(x_cm=x*100,y_cm=y*100)
        for name,t,start,direction in [('factory',native,-.1,1),('new_body',body,-.1,1),('old_seat',old,.2,-1),('new_seat',base,.2,-1)]:
            hit,normal,index,d=t.ray_cast(Vector((x,y,start)),Vector((0,0,direction)))
            row[name+'_z_mm']=hit.z*1000 if hit else None
        row['new_body_gap_mm']=row['new_body_z_mm']-row['new_seat_z_mm']
        row['factory_gap_mm']=row['factory_z_mm']-row['new_seat_z_mm']
        samples.append(row)
r=dict(scope='Bipod saddle contact only; no game/animation test',samples=samples,
       contact_pad_compression_mm=[-max(s['new_body_gap_mm'] for s in samples),-min(s['new_body_gap_mm'] for s in samples)],
       max_factory_gap_mm=max(s['factory_gap_mm'] for s in samples),
       open_gap_in_new_mount=any(s['new_body_gap_mm']>.15 or s['factory_gap_mm']>.15 for s in samples),
       hinge_cm=[0,-45,2.2],legs_and_deployment_timeline_changed=False)
(O/'bipod-fit.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r),flush=True)
