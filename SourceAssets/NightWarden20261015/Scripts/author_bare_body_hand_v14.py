"""Remove rejected clothing and repair left digit vertices attached to the thigh.

Restore the complete body extracted from V10 into RecoveryInputs, including covered skin. Find the hand's
connected surface in the reported area (welding only in the selection graph,
not in the mesh), then redistribute foreign weights to its existing hand bones.
All vertex coordinates, UVs, faces and original bone bind transforms are retained.
"""
import bpy,json,numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Matrix,Vector

BASE=Path(__file__).resolve().parents[1];OUT=BASE/'V14BareBodyHand'
for folder in ['Authoring','Exports','Records']:(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'RecoveryInputs/NightWarden_CompleteBody_PreHandRepair.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
body=bpy.data.objects['NW10_CompleteOriginalBody_Source']
rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data_clear();rig.data.pose_position='REST'
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
C=Matrix(((0,-100,0,0),(-100,0,0,0),(0,0,100,0),(0,0,0,1)))
points=np.array([list(C@(body.matrix_world@v.co)) for v in body.data.vertices])
edges=np.array([e.vertices[:] for e in body.data.edges],dtype=int)
names=[g.name for g in body.vertex_groups]
weights=np.zeros((len(points),len(names)))
for v in body.data.vertices:
    for g in v.groups:weights[v.index,g.group]=g.weight
region=(points[:,1]<-30)&(points[:,2]<100)&(points[:,2]>60)&(points[:,0]>-12)&(points[:,0]<22)
ids=np.flatnonzero(region)
_,weld=np.unique(np.round(points[ids],4),axis=0,return_inverse=True)
parent=list(range(int(weld.max())+1))
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
lookup=np.full(len(points),-1,int);lookup[ids]=weld
for a,b in lookup[edges[np.all(region[edges],axis=1)]]:
    a=root(a);b=root(b)
    if a!=b:parent[b]=a
roots=np.array([root(i) for i in weld])
hand_names={'Bone_%03d'%i for i in list(range(19,24))+list(range(29,37))}
hand_groups=[i for i,n in enumerate(names) if n in hand_names]
hand_weight=weights[:,hand_groups].sum(1)
hand_ids=[]
for r,count in Counter(roots).items():
    component=ids[roots==r]
    if hand_weight[component].mean()>.8:hand_ids.extend(component.tolist())
if not hand_ids:raise RuntimeError('No left-hand surface found in the authored area')
changes=[]
for i in hand_ids:
    before={names[j]:float(w) for j,w in enumerate(weights[i]) if w>1e-8}
    foreign={n:w for n,w in before.items() if n not in hand_names}
    if sum(foreign.values())<1e-6:continue
    retained={n:w for n,w in before.items() if n in hand_names};total=sum(retained.values())
    if total<.01:raise RuntimeError('No usable original hand weights at vertex '+str(i))
    after={n:w/total for n,w in retained.items()}
    v=body.data.vertices[i]
    for g in list(v.groups):body.vertex_groups[g.group].remove([i])
    for n,w in after.items():body.vertex_groups[n].add([i],w,'REPLACE')
    changes.append({'vertex':i,'position_cm':points[i].tolist(),'before':before,'after':after})

# Restore the full skin mesh, not the V10 copy with covered faces removed.
# The saved output contains no wrap, waistband, underlap or cloth proxy.
removed=[]
for o in list(scene.objects):
    if o not in (body,rig):
        removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
body.name='NW14_CompleteBody_HandRepair'
body.hide_render=False;body.hide_viewport=False;body.hide_set(False)
rig.hide_render=False;rig.hide_viewport=False;rig.hide_set(False)
body['repair']='Left digit thigh contamination removed; original positions, topology and hand-weight proportions preserved'
rig['revision']='V14BareBodyHand'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/NightWarden_BareBody_HandRepair_V14.blend'))

# Established centimeter/axis export used by the original 46-bone animations.
cm=rig.copy();cm.data=rig.data.copy();scene.collection.objects.link(cm);cm.name='Armature'
cm.data.transform(Matrix.Scale(100,4)@rig.matrix_world);cm.matrix_world=Matrix.Identity(4)
clone=body.copy();clone.data=body.data.copy();scene.collection.objects.link(clone)
clone.data.transform(Matrix.Scale(100,4)@body.matrix_world);clone.parent=cm
clone.matrix_parent_inverse=Matrix.Identity(4);clone.matrix_world=Matrix.Identity(4)
for mod in clone.modifiers:
    if mod.type=='ARMATURE':mod.object=cm
bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);cm.select_set(True)
bpy.context.view_layer.objects.active=cm;scene.unit_settings.scale_length=.01
fbx=OUT/'Exports/SK_NightWarden_BareBody_HandRepair_V14.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    global_scale=1.,add_leaf_bones=False,bake_anim=False,use_armature_deform_only=True,
    armature_nodetype='NULL',mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
report={'stage':'complete_body_and_left_hand_weights_authored','fbx':str(fbx),
    'source':'RecoveryInputs/NightWarden_CompleteBody_PreHandRepair.blend: NW10_CompleteOriginalBody_Source',
    'body_vertices':len(body.data.vertices),'body_faces':len(body.data.polygons),
    'bones':len(rig.data.bones),'left_hand_surface_vertices':len(hand_ids),
    'repaired_vertices':len(changes),'weight_changes':changes,'removed_objects':removed,
    'vertex_positions_changed':False,'uvs_or_topology_changed':False,
    'clothing':False,'cloth_simulation':False,'body_animation_tracks_changed':False,
    'game_tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NW14_BODY_AUTHORED '+json.dumps({k:v for k,v in report.items() if k!='weight_changes'}),flush=True)
