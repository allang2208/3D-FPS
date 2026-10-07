"""Rebind the original M27 connected surfaces; retain existing motion timing."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector, Matrix, kdtree

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT=BASE/'BindingV2'; OUT=ROOT/'Delivery'; OUT.mkdir(parents=True,exist_ok=True)
topology=np.load(ROOT/'connected_source.npz')
p=topology['points']; edges=topology['edges']; inverse=topology['inverse']; component=topology['component']
source=np.load(BASE/'ProductionV1/source_geometry.npz'); ground=float(source['positions'][:,1].min())
adj=[[] for _ in p]
for a,b in edges: adj[a].append(int(b)); adj[b].append(int(a))
def region(mask,seed):
    permitted=np.flatnonzero(mask)
    start=int(permitted[np.argmin(np.sum((p[permitted]-seed)**2,axis=1))])
    seen=np.zeros(len(p),bool); seen[start]=True; stack=[start]
    while stack:
        v=stack.pop()
        for nxt in adj[v]:
            if mask[nxt] and not seen[nxt]: seen[nxt]=True; stack.append(nxt)
    return seen
def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1); return t*t*(3-2*t)
def co(xyz):
    x,y,z=xyz; return Vector((x*100,-z*100,(y-ground)*100))

bpy.ops.wm.open_mainfile(filepath=str(BASE/'ProductionV1/Delivery/MantisM27_ProductionV1.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
body=next(o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)>100000)
names=[b.name for b in rig.data.bones]; lookup={n:i for i,n in enumerate(names)}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
old_rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
clips={}
manifest=json.loads((BASE/'ProductionV1/Delivery/motion_manifest.json').read_text(encoding='utf-8'))
# Read animation transforms as production input before changing the bind pose.
for role,info in manifest['clips'].items():
    action=bpy.data.actions['A_M27_'+role]; rig.animation_data.action=action
    if action.slots: rig.animation_data.action_slot=action.slots[0]
    frames=[]
    for f in range(1,info['frames']+1):
        bpy.context.scene.frame_set(f)
        frames.append({n:rig.pose.bones[n].matrix.copy() for n in names})
    clips[role]=frames
rig.animation_data.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for side,sign in [('l',1),('r',-1)]:
    def c(x,y,z):return co((sign*x,y,z))
    elbow=c(.323,.31,-.061); wrist=c(.425,0,-.011)
    rig.data.edit_bones['upperarm_'+side].tail=elbow
    lower=rig.data.edit_bones['lowerarm_'+side]; lower.head=elbow; lower.tail=wrist
    hand=rig.data.edit_bones['hand_'+side]; hand.head=wrist; hand.tail=c(.45,-.07,0)
    br=rig.data.edit_bones['blade_root_'+side]; br.head=c(.365,.16,-.035); br.tail=c(.485,-.35,.035)
    bm=rig.data.edit_bones['blade_mid_'+side]; bm.head=br.tail; bm.tail=c(.350,-.785,.050)
    bt=rig.data.edit_bones['blade_tip_'+side]; bt.head=bm.tail; bt.tail=c(.345,-.81,.052)
    for n in ['upperarm','lowerarm','hand','blade_root','blade_mid','blade_tip']:
        rig.data.edit_bones[n+'_'+side].align_roll(Vector((0,-1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}

# Collapse UV duplicates for weight authoring only, never for display geometry.
old=np.zeros((len(body.data.vertices),len(names)),np.float32)
groups={g.index:lookup[g.name] for g in body.vertex_groups if g.name in lookup}
for vertex in body.data.vertices:
    for group in vertex.groups:
        if group.group in groups:old[vertex.index,groups[group.group]]=group.weight
W=np.zeros((len(p),len(names)),np.float32)
np.add.at(W,inverse,old); W/=np.bincount(inverse)[:,None]
x,y,z=p.T
regions={}; arm_all=np.zeros(len(p),bool); rigid=np.zeros(len(p),bool)
for side,sign in [('l',1),('r',-1)]:
    mask=region(y<.50,np.array([sign*.46,-.35,.035]))
    regions['arm_'+side]=mask; arm_all|=mask
    W[mask]=0
    upper=smooth(.25,.40,y[mask])
    W[mask,lookup['upperarm_'+side]]=upper
    W[mask,lookup['lowerarm_'+side]]=1-upper
    blade=mask&(y<=.22)
    W[blade]=0; W[blade,lookup['blade_root_'+side]]=1
    # These helper bones inherit exactly the same rigid motion as the forearm.
    # Blend the skin assignment across the elbow without adding a blade bend.
    blend=mask&(y>.22)&(y<.26)
    t=smooth(.22,.26,y[blend])
    W[blend]=0; W[blend,lookup['blade_root_'+side]]=1-t
    W[blend,lookup['lowerarm_'+side]]=t
    rigid|=blade
for side,sign in [('l',1),('r',-1)]:
    foot=region((y<-.75)&~arm_all,np.array([sign*.21,-.90,.04]))
    leg=region((y<-.055)&~arm_all&(x*sign>0)&(z>-.205),np.array([sign*.18,-.65,-.10]))
    regions['foot_'+side]=foot; regions['leg_'+side]=leg
    ids=leg|foot; W[ids]=0
    knee=smooth(-.425,-.285,y[ids]); hip=smooth(-.17,-.055,y[ids])
    W[ids,lookup['calf_'+side]]=1-knee
    W[ids,lookup['thigh_'+side]]=knee*(1-hip)
    W[ids,lookup['pelvis']]=knee*hip
    # Entire connected foot, including outer claws and rear toes, is assigned
    # to its foot bone. Only the ankle collar blends into the same-side calf.
    W[foot]=0
    ankle=smooth(-.85,-.75,y[foot])
    W[foot,lookup['foot_'+side]]=1-ankle; W[foot,lookup['calf_'+side]]=ankle
    rigid|=foot&(y<=-.85)

# The cut surfaces become smooth joint collars on the actual surface graph.
# Disconnected scythes cannot borrow weights from nearby feet or torso.
editable=(
    ((np.abs(x)>.14)&(y>.46)&(y<.63)) |
    (arm_all&(y>.22)&(y<.43)) |
    ((regions['leg_l']|regions['leg_r'])&(((y>-.46)&(y<-.25))|((y>-.19)&(y<.01)))) |
    ((regions['foot_l']|regions['foot_r'])&(y>-.85))
) & ~rigid
directed=np.concatenate([edges,edges[:,::-1]])
rows=directed[:,0]; cols=directed[:,1]
selected=editable[rows]; rows=rows[selected]; cols=cols[selected]
degree=np.bincount(rows,minlength=len(p)); active=np.flatnonzero(degree)
for iteration in range(28):
    avg=np.zeros_like(W)
    for bone in range(len(names)):
        avg[:,bone]=np.bincount(rows,weights=W[cols,bone],minlength=len(p))
    avg[active]/=degree[active,None]
    W[active]=W[active]*.35+avg[active]*.65

# Detached chain slivers inherit the nearest intact connected surface. They
# stay intact as islands instead of being divided by world-coordinate bands.
counts=np.bincount(component); main=int(np.argmax(counts)); main_ids=np.flatnonzero(component==main)
tree=kdtree.KDTree(len(main_ids))
for v in main_ids:tree.insert(Vector(p[v]),int(v))
tree.balance()
for label in np.flatnonzero(counts<100):
    ids=np.flatnonzero(component==label); center=p[ids].mean(axis=0)
    _,nearest,_=tree.find(Vector(center)); W[ids]=W[nearest]

# Keep at most four local influences and assign identical values to every UV
# copy. Eliminate the old generic coordinate field from both feet and blades.
top=np.argpartition(W,-4,axis=1)[:,-4:]; limited=np.zeros_like(W)
row=np.arange(len(W))[:,None]; limited[row,top]=W[row,top]
limited/=limited.sum(axis=1,keepdims=True)
weights=limited[inverse]
body.vertex_groups.clear()
for b,name in enumerate(names):
    group=body.vertex_groups.new(name=name)
    q=np.rint(weights[:,b]*65535).astype(np.int32)
    for value in np.unique(q):
        if value:group.add(np.flatnonzero(q==value).tolist(),float(value)/65535,'REPLACE')
np.savez_compressed(ROOT/'binding_weights_v2.npz',weights=limited,names=np.asarray(names),inverse=inverse,
                    **{name:np.flatnonzero(mask) for name,mask in regions.items()})

def select(mesh=False):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    if mesh:body.select_set(True)
    bpy.context.view_layer.objects.active=rig
def export(path,animation=False):
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'} if animation else {'ARMATURE','MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1,axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',mesh_smooth_type='FACE',
        use_mesh_modifiers=False,bake_anim=animation,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='STRIP')
select(True); bpy.context.scene.frame_set(0)
export(OUT/'SK_MantisM27_BindingV2.fbx')
for role,frames in clips.items():
    action=bpy.data.actions.new('A_M27_'+role+'_BindingV2');action.use_fake_user=True;rig.animation_data.action=action
    bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=len(frames)
    for frame,old_transforms in enumerate(frames,1):
        targets={}
        for name in names:
            parent=parents[name]
            target=targets[parent]@local[name] if parent else local[name].copy()
            location=target.translation.copy()
            rotation=old_transforms[name].to_quaternion()@old_rest[name].to_quaternion().inverted()@rest[name].to_quaternion()
            target=rotation.to_matrix().to_4x4();target.translation=location
            if name in ('root','pelvis'):target.translation=old_transforms[name].translation
            targets[name]=target
            basis=local[name].inverted()@(targets[parent].inverted()@target if parent else target)
            pb=rig.pose.bones[name];pb.location=basis.translation;pb.rotation_mode='QUATERNION';pb.rotation_quaternion=basis.to_quaternion();pb.scale=(1,1,1)
            pb.keyframe_insert('location',frame=frame,group=name);pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
    bpy.context.scene.frame_set(1);select();filename='A_M27_'+role+'_BindingV2.fbx';export(OUT/filename,True)
    manifest['clips'][role]['file']=filename
    print('M27 BindingV2 exported '+role,flush=True)
rig.animation_data.action=bpy.data.actions['A_M27_Idle_BindingV2'];bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=manifest['clips']['Idle']['frames'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_BindingV2.blend'))
manifest['revision']='BindingV2';manifest['mesh_file']='SK_MantisM27_BindingV2.fbx'
manifest['source']='../../MeshyImport20261005V1/Source/Meshy_AI_M_27_Mawbound_Horror_1005150638_texture.glb'
manifest['previous_user_feedback']='Foot stretching during movement and blade stretching during attacks; ProductionV1 binding rejected.'
manifest['binding_changes']=['Connected-surface arm and foot assignment','Rigid whole scythe and claw cores','Local ankle/elbow/knee/shoulder blends','Fitted elbow and blade reference bones','Existing action deltas and timings transferred to fitted bind pose']
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'binding_recipe.json').write_text(json.dumps({'revision':'BindingV2','regions':{n:int(m.sum()) for n,m in regions.items()},
    'source_display_unchanged':True,'uv_unchanged':True,'action_timing_unchanged':True,'tested':False,'user_review_pending':True,
    'joint_changes':{n:{'old_cm':list(old_rest[n].translation),'new_cm':list(rest[n].translation)} for n in names if (rest[n].translation-old_rest[n].translation).length>.001}},ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_BINDING_V2_AUTHORED',flush=True)
