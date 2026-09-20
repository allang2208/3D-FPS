"""Fit only the three right-thumb rotations against the actual axe surface."""
import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/AxeTwoHandPose20260919/H4/Axe_TwoHand_H4_Idle_Equip_Editable.blend'))
rig=bpy.data.objects['SK_Harvest_Axe_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export'];axe=bpy.data.objects['Harvest_Axe']
scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['A_Harvest_Axe_Idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
names=['thumb_01_r','thumb_02_r','thumb_03_r']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={b.name:b.matrix.copy() for b in rig.pose.bones}
lr={n:rest[rig.data.bones[n].parent.name].inverted()@rest[n] for n in names}
ids=[v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if arms.vertex_groups[g.group].name in names)>.25]
dg=bpy.context.evaluated_depsgraph_get();obj=axe.evaluated_get(dg);mesh=obj.to_mesh()
tree=BVHTree.FromPolygons([rig.matrix_world.inverted()@obj.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons]);obj.to_mesh_clear()
to_rig=rig.matrix_world.inverted()@arms.matrix_world
vertices=np.array([[*(to_rig@arms.data.vertices[i].co),1] for i in ids])
weights={}
for j,i in enumerate(ids):
    for g in arms.data.vertices[i].groups:
        n=arms.vertex_groups[g.group].name
        if n in pose:
            weights.setdefault(n,np.zeros(len(ids)))[j]=g.weight
pre={n:(vertices@np.array(rest[n].inverted()).T)*w[:,None] for n,w in weights.items()}
fixed=sum((v@np.array(pose[n]).T for n,v in pre.items() if n not in names),np.zeros((len(ids),4)))
tip_ids=np.array([j for j,i in enumerate(ids) if any(arms.vertex_groups[g.group].name=='thumb_03_r' and g.weight>.65 for g in arms.data.vertices[i].groups)])
thumb_weight=sum((weights.get(n,np.zeros(len(ids))) for n in names),np.zeros(len(ids)))
active_ids=np.flatnonzero(thumb_weight>.65)
tool_inv=np.array(pose['WPN_root'].inverted())
baseline_points=fixed+sum((pre[n]@np.array(pose[n]).T for n in names),np.zeros_like(fixed))
baseline_tip_tool=(baseline_points[tip_ids].mean(axis=0)@tool_inv.T)[:3]
limits=[(-12,12),(-40,40),(-24,24),(0,50),(0,40)]

def frames(x):
    result={}
    for j,n in enumerate(names):
        angles=x[:3] if j==0 else [0,0,x[j+2]]
        basis=Euler([math.radians(a) for a in angles],'XYZ').to_matrix().to_4x4()
        parent=pose['hand_r'] if j==0 else result[names[j-1]]
        result[n]=parent@lr[n]@basis
    return result

def evaluate(x, details=False):
    p=frames(x)
    points=fixed+sum((pre[n]@np.array(p[n]).T for n in names),np.zeros_like(fixed))
    distances=[]
    for v in points[:,:3]:
        point=Vector(v);near,normal,_,distance=tree.find_nearest(point)
        distances.append(distance*1000*(1 if (point-near).dot(normal)>=0 else -1))
    d=np.array(distances)
    # Surface volume first, but also retain a relaxed opposing pad near the handle.
    penetration=np.maximum(.6-d[active_ids],0)
    near_tip=np.sort(d[tip_ids])[:max(1,len(tip_ids)//5)].mean()
    score=np.mean(penetration**2)*5 + max(0.,.6-d[active_ids].min())**2*2.5
    score+=max(0.,near_tip-1.5)**2*1.2
    tip_tool=(points[tip_ids].mean(axis=0)@tool_inv.T)[:3]
    score+=max(0.,abs((tip_tool[2]-baseline_tip_tool[2])*1000)-4.)**2*.65
    score+=np.sum((np.array(x)-np.array([0,0,0,24,20]))**2*np.array([.012,.007,.007,.003,.004]))
    return (score,{'minimum_signed_surface_mm':float(d.min()),'inside_vertices':int((d<-.1).sum()),
                   'thumb_dominant_minimum_mm':float(d[active_ids].min()),
                   'thumb_dominant_inside_vertices':int((d[active_ids]<-.1).sum()),
                   'tip_patch_mm':float(near_tip),'tip_axial_change_mm':float((tip_tool[2]-baseline_tip_tool[2])*1000)},p) if details else score

start=[0.,0.,0.,24.,24.]
best=start[:];score=evaluate(best)
for y in (-24,-12,0,12,24,36):
    for z in (-24,-12,0,12,24):
        for curl in (16.,32.,48.):
            candidate=[0.,float(y),float(z),curl,20.]
            value=evaluate(candidate)
            if value<score:best,score=candidate,value
for step in (8.,4.,2.,1.,.5):
    for iteration in range(15):
        changed=False
        for index,(low,high) in enumerate(limits):
            for sign in (-1,1):
                candidate=best[:];candidate[index]=max(low,min(high,candidate[index]+sign*step))
                value=evaluate(candidate)
                if value<score-1e-8:best,score,changed=candidate,value,True
        if not changed:break
    print('THUMB_FIT',step,best,score,flush=True)
# A small outward authoring allowance keeps the visible thumb off the rough shaft.
best[1]=min(limits[1][1],best[1]+1.)
_,before,_=evaluate(start,True)
_,after,corrected= evaluate(best,True)
relative={n:pose['hand_r'].inverted()@m for n,m in corrected.items()}
result={'rotation_parameters_deg':best,'before':before,'after':after,
        'tool_local_hand':[list(row) for row in pose['WPN_root'].inverted()@pose['hand_r']],
        'hand_relative_thumb':{n:[list(row) for row in m] for n,m in relative.items()},
        'scope':'Three thumb rotations only; wrist, other digits, bone lengths, scale and translations unchanged.'}
(HERE/'thumb_fit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'parameters':best,'before':before,'after':after}),flush=True)
