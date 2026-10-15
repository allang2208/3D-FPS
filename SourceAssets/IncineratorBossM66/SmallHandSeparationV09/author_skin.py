"""Repair small-arm/oral ownership while preserving V08 rig and animation."""
import bpy,json
import numpy as np
from pathlib import Path
from mathutils import Matrix

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'SmallHandSeparationV09'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'HandContinuityV08/Authoring/M66_hand_continuity_v08.blend'))
mesh=bpy.data.objects['M66_Body'];rig=bpy.data.objects['M66_Rig']
names=[g.name for g in mesh.vertex_groups];index={n:i for i,n in enumerate(names)}
pos=np.array([v.co[:] for v in mesh.data.vertices]);weights=np.zeros((len(pos),len(names)))
for vertex in mesh.data.vertices:
    for group in vertex.groups:weights[vertex.index,group.group]=group.weight
result=weights.copy();hand=np.load(ROOT/'Records/small_arm_surface.npy')

def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0.,1.);return t*t*(3-2*t)

def column_mask(numbers):return np.isin(names,['Bone_%03d'%i for i in numbers])

arm=column_mask(list(range(29,34))+list(range(38,54)))
distal=column_mask([29,30]+list(range(38,54)))
x,y,z=pos.T
# Clean both directions: hand surface cannot inherit body/legs; body surface
# cannot inherit the small palm/fingers. Do not infer ownership from weights.
hand_clean=hand.astype(float)*(1-smooth(1.90,2.05,z))
hand_target=weights.copy();hand_target[:,~arm]=0
arm_total=hand_target.sum(1)
for i in np.flatnonzero(hand&(arm_total<1e-7)):
    hand_target[i,index['Bone_031']]=1.
hand_target/=np.maximum(hand_target.sum(1,keepdims=True),1e-12)
result=result*(1-hand_clean[:,None])+hand_target*hand_clean[:,None]

# On the oral sheet use a common smooth pelvis/spine field, including vertices
# previously misclassified as fingers. Upper/lateral attachment bands fade into
# the existing neck/shoulder skin. The real hand has a topology-based exclusion.
oral=smooth(-.60,-.40,x)*(1-smooth(.40,.65,x))
oral*=1-smooth(-.30,-.10,y)
oral*=smooth(.75,1.05,z)*(1-smooth(2.65,3.05,z))
oral[hand]=0.
upper=smooth(1.70,2.50,z)
body=np.zeros_like(weights)
body[:,index['Bone_001']]=1-upper
body[:,index['Bone_007']]=upper*.25
body[:,index['Bone_006']]=upper*.75
result=result*(1-oral[:,None])+body*oral[:,None]

# Finger/palm contamination also extends beyond the mouth mask. Preserve the
# local body's existing skin there, but remove all distal-hand influence.
outside=~hand
result[np.ix_(outside,distal)]=0.
empty=outside&(result.sum(1)<1e-7)
result[empty]=body[empty]
result/=np.maximum(result.sum(1,keepdims=True),1e-12)

# UV seams share an anatomical vertex; write an identical normalized skin to
# every copy. Limit this to repaired vertices and their coincident counterparts.
_,weld=np.unique(np.rint(pos/1e-6).astype(np.int64),axis=0,return_inverse=True)
touched=np.any(np.abs(result-weights)>1e-6,axis=1)
counts=np.bincount(weld);summed=np.zeros((len(counts),len(names)))
np.add.at(summed,weld,result);summed/=counts[:,None]
edited_weld=np.zeros(len(counts),bool);edited_weld[weld[touched]]=True
changed=edited_weld[weld];result[changed]=summed[weld[changed]]
for i in np.flatnonzero(changed):
    values=result[i];keep=np.argsort(values)[-8:];keep=keep[values[keep]>1e-6]
    total=values[keep].sum()
    for group in list(mesh.data.vertices[i].groups):mesh.vertex_groups[group.group].remove([int(i)])
    for j in keep:mesh.vertex_groups[int(j)].add([int(i)],float(values[j]/total),'REPLACE')

action=rig.animation_data.action
rig['stage']='V09 topology-separated small hand and oral/abdominal skin'
mesh['M66_surface_repair']='Small hand surface follows its arm only; mouth lining and abdominal tissue follow pelvis/spine'
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/SK_M66_SmallHandSeparation_V09.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,use_mesh_modifiers=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
rig.animation_data.action=action
if action and action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.context.scene.frame_set(0)
authoring=ROOT/'Authoring/M66_small_hand_separation_v09.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
report={'source':str(BASE/'HandContinuityV08/Authoring/M66_hand_continuity_v08.blend'),
    'fbx':str(fbx),'authoring':str(authoring),'edited_vertices':int(changed.sum()),
    'actual_small_hand_vertices':int(hand.sum()),'oral_transition_vertices':int((oral>1e-6).sum()),
    'removed_foreign_hand_weight':float((weights[hand_clean>.99][:,~arm]).sum()),
    'removed_distal_hand_weight_from_body':float(weights[outside][:,distal].sum()),
    'vertices':len(pos),'bones':len(rig.data.bones),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
    'geometry_modified':False,'uv_modified':False,'animation_modified':False,
    'preserved_attack':'HandContinuityV08/A_M66_ClawSweep_V08',
    'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
(ROOT/'Records/skin_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_SMALL_HAND_SKIN_AUTHORED '+json.dumps(report),flush=True)
