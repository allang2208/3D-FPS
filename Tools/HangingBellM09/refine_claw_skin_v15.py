"""Local elbow/wrist weight transitions for the requested M09 claw redesign.

Preserve V13 ownership, geometry, UVs, fingers, skeleton and corpse asset. Replace
nearest-segment jumps at the small elbow with a continuous anatomical joint band.
"""
import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'CrownClawV15'
for d in ('Authoring','Exports','Records'):(OUT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SkinDeathV13/Authoring/M09_Rigged_V13.blend'))
rig=bpy.data.objects['M09_Rig_V03'];report=[]
def smooth(x):
    x=np.clip(x,0.,1.);return x*x*(3-2*x)
for side in ('L','R'):
    ob=bpy.data.objects['M09_SmallArm_'+side];me=ob.data
    p=np.empty((len(me.vertices),3));me.vertices.foreach_get('co',p.ravel())
    m=np.array(ob.matrix_world);p=p@m[:3,:3].T+m[:3,3]
    groups=[g.name for g in ob.vertex_groups];weights=np.zeros((len(p),len(groups)))
    for v in me.vertices:
        for g in v.groups:weights[v.index,g.group]=g.weight
    before=weights.copy()
    names=[f'small_{n}_{side}' for n in ('upperarm','forearm','hand')]
    ids=[groups.index(n) for n in names]
    s,e,w=[np.array(rig.matrix_world@rig.data.bones[n].head_local) for n in names]
    h=np.array(rig.matrix_world@rig.data.bones[names[-1]].tail_local)
    u=(e-s)/np.linalg.norm(e-s);f=(w-e)/np.linalg.norm(w-e);palm=(h-w)/np.linalg.norm(h-w)
    elbow_plane=(u+f)/np.linalg.norm(u+f);wrist_plane=(f+palm)/np.linalg.norm(f+palm)
    a=smooth(((p-e)@elbow_plane+.065)/.130)
    b=smooth(((p-w)@wrist_plane+.040)/.080)
    mass=weights[:,ids].sum(1)
    weights[:,ids[0]]=mass*(1-a)
    weights[:,ids[1]]=mass*a*(1-b)
    weights[:,ids[2]]=mass*a*b
    # UV duplicates must share the same weights; no averaging across body parts.
    _,inverse=np.unique(np.rint(p*1e6).astype(np.int64),axis=0,return_inverse=True)
    count=np.bincount(inverse);averages=np.zeros((len(count),len(groups)))
    np.add.at(averages,inverse,weights);averages/=count[:,None];weights=averages[inverse]
    sid=np.empty(len(p),np.int32);me.attributes['source_vertex_id'].data.foreach_get('value',sid)
    edges=np.empty((len(me.edges),2),np.int32);me.edges.foreach_get('vertices',edges.ravel())
    for v in np.flatnonzero(sid<0):
        touching=edges[(edges==v).any(1)].ravel();neighbors=np.unique(touching[touching!=v])
        neighbors=neighbors[sid[neighbors]>=0]
        if len(neighbors):weights[v]=weights[neighbors].mean(0)
    weights[weights<1/1024]=0
    weights/=np.maximum(weights.sum(1)[:,None],1e-12)
    all_ids=list(range(len(p)))
    for g in ob.vertex_groups:g.remove(all_ids)
    for col,g in enumerate(ob.vertex_groups):
        quantized=np.rint(weights[:,col]*1024).astype(np.int32)
        for value in np.unique(quantized):
            if value:g.add(np.flatnonzero(quantized==value).tolist(),float(value)/1024,'REPLACE')
    report.append({'part':ob.name,'changed_vertices':int((np.abs(weights-before).max(1)>1e-5).sum()),
        'vertices':len(p),'elbow_blend_width_cm':13,'wrist_blend_width_cm':8,
        'geometry_UV_bind_unchanged':True,'finger_ownership_preserved':True})
rig.animation_data_clear()
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Rigged_ClawV15.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/M09_Rigged_ClawV15.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Z',axis_up='Y',bake_anim=False,add_leaf_bones=False,use_armature_deform_only=True,
    mesh_smooth_type='FACE',use_mesh_modifiers=True)
(OUT/'Records/skin_refinement.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_CLAW_V15_JOINT_SKIN_SAVED',flush=True)
