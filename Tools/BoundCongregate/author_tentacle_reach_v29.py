"""Refine only the expandable distal organ in the accepted V25 dressed mesh.

The bind skeleton and garment geometry remain identical, retaining CombatV28.
Additional longitudinal samples and centreline skin weights support runtime
deployment to 30 m without stretching the welded shoulder or thick root.
"""
from pathlib import Path
import json, shutil, math
import bpy, bmesh, numpy as np
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'TentacleReachV29';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GarmentDrapeV25/BoundCongregate_GarmentDrapeV25.blend'))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
if rig.animation_data:rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
body=bpy.data.objects['BC_Flesh']
nodes=np.array([rig.data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(57)])
segments=np.diff(nodes,axis=0);lengths=np.linalg.norm(segments,axis=1)
arc=np.r_[0,np.cumsum(lengths)]
slots={i for i,m in enumerate(body.data.materials) if m and m.name=='BC_AttackTentacle'}
group_ids={g.index:int(g.name.rsplit('_',1)[1]) for g in body.vertex_groups if g.name.startswith('attack_tentacle_')}
before=len(body.data.vertices)
bm=bmesh.new();bm.from_mesh(body.data)
deform=bm.verts.layers.deform.active
def distal(v):
    return sum(w for g,w in v[deform].items() if group_ids.get(g,-1)>=14)>.98
# Two new samples per existing distal edge; the collar and garment seam are
# untouched. BMesh interpolates the original UVs and all point/corner channels.
edges=[e for e in bm.edges if all(distal(v) for v in e.verts)
       and all(f.material_index in slots for f in e.link_faces)]
bmesh.ops.subdivide_edges(bm,edges=edges,cuts=2,use_grid_fill=True,smooth=0.)
bm.to_mesh(body.data);bm.free();body.data.update()
selected=set()
for face in body.data.polygons:
    if face.material_index in slots:selected.update(face.vertices)
changed=0
for i in selected:
    v=body.data.vertices[i]
    old=[(group_ids[g.group],g.weight) for g in v.groups if g.group in group_ids]
    if not old or sum(w for j,w in old if j>=13)<.999:continue
    approximate=sum(j*w for j,w in old)/sum(w for _,w in old)
    first=max(12,int(approximate)-4);last=min(56,int(approximate)+5)
    p=np.array(v.co[:]);delta=p-nodes[first:last]
    t=np.clip(np.einsum('ij,ij->i',delta,segments[first:last])/lengths[first:last]**2,0.,1.)
    q=nodes[first:last]+segments[first:last]*t[:,None]
    nearest=int(np.argmin(np.linalg.norm(q-p,axis=1)));j=first+nearest;u=float(t[nearest])
    centre=q[nearest];radial=p-centre
    s=float(np.clip((arc[j]+u*lengths[j]-arc[13])/(arc[-1]-arc[13]),0,1))
    blend=float(np.clip((j+u-13)/5,0,1));blend=blend*blend*(3-2*blend)
    # Retain the sculpted surface, gently reduce isolated lumps/spikes and give
    # the long strand a continuous muscular-to-whip taper (metre source units).
    radius=float(np.linalg.norm(radial))
    envelope=.078*(1-s)**.7+.025
    fitted=min(radius,envelope)
    if radius>1.e-7:v.co=Vector(centre+radial*((1-blend)+blend*fitted/radius))
    # Barycentric adjacent stations preserve longitudinal location as the chain
    # deploys; the old four-bone Gaussian produced bunching during extension.
    old_weights={g.group:g.weight for g in v.groups}
    new_weights={g:w*(1-blend) for g,w in old_weights.items()}
    for bone,w in ((j,1-u),(j+1,u)):
        group=body.vertex_groups[f'attack_tentacle_{bone:02d}'].index
        new_weights[group]=new_weights.get(group,0)+blend*w
    for g in list(v.groups):body.vertex_groups[g.group].remove([i])
    entries=sorted(new_weights.items(),key=lambda item:item[1],reverse=True)[:8]
    total=sum(w for _,w in entries)
    for g,w in entries:
        if w>1.e-7:body.vertex_groups[g].add([i],float(w/total),'REPLACE')
    changed+=1
for p in body.data.polygons:
    if p.material_index in slots:p.use_smooth=True
body.data.update()
shutil.copy2(ROOT/'GarmentDrapeV25/collision_recipe.json',OUT/'collision_recipe.json')
report=dict(revision='TentacleReachV29',maximum_attack_distance_cm=3000,
    source='GarmentDrapeV25',body_vertices_before=before,body_vertices_after=len(body.data.vertices),
    refined_distal_vertices=changed,ref_chain_cm=float(arc[-1]*100),
    bones=57,protected_root_bones='00..13',retained='V25 garments, seam, skeleton, UVs, body and accepted CombatV28 flurry',
    geometry='distal subdivision, restrained taper, adjacent-station skinning',
    deployment='runtime distance-dependent extension, transverse thinning and progressive recovery',
    rendered=False,gameplay_tested=False)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_TentacleReachV29.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in scene.objects:
    if obj.type in ('MESH','ARMATURE'):obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_TentacleReachV29.fbx'),
    use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP',
    colors_type='SRGB',prioritize_active_color=True)
print('TENTACLE_REACH_V29_EXPORTED '+json.dumps(report),flush=True)
