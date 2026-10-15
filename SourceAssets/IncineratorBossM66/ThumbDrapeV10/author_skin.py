"""Protect the complete giant hand and rig the four hanging tissue lobes."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'ThumbDrapeV10'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SmallHandSeparationV09/Authoring/M66_small_hand_separation_v09.blend'))
mesh=bpy.data.objects['M66_Body'];rig=bpy.data.objects['M66_Rig'];action=rig.animation_data.action
pos=np.array([v.co[:] for v in mesh.data.vertices]);names=[g.name for g in mesh.vertex_groups]
weights=[{names[g.group]:g.weight for g in v.groups if g.weight>1e-7} for v in mesh.data.vertices]
result=[dict(w) for w in weights]
top=np.load(ROOT/'Records/topology.npz');weld=top['weld'];unique=top['unique_ids'];labels=top['lower_component']
hand=np.load(ROOT/'Records/giant_hand.npy')

def descendant(bone,root):
    while bone:
        if bone.name==root:return True
        bone=bone.parent
    return False

arm={b.name for b in rig.data.bones if descendant(b,'Bone_027')}
hand_changed=[]
for i in np.flatnonzero(hand):
    kept={name:value for name,value in result[i].items() if name in arm}
    total=sum(kept.values())
    if total<1e-6:continue
    if sum(v for n,v in result[i].items() if n not in arm)>1e-6:
        result[i]={n:v/total for n,v in kept.items()};hand_changed.append(int(i))

# The tissue component is identified by a point on its long centre lobe, not
# by source bone labels. The hands and two legs are separate below this section.
points=pos[unique];seed=np.linalg.norm(points-[.31,-.285,.85],axis=1).argmin()
drape=labels==labels[seed]
# Detached tips within the same tissue envelope retain their visual ownership.
for label in np.unique(labels):
    ids=np.flatnonzero(labels==label)
    if len(ids)>24 or len(ids)<3:continue
    p=points[ids];lo=p.min(0);hi=p.max(0)
    if lo[0]>0 and hi[0]<.45 and lo[1]>-.46 and hi[1]<-.15 and lo[2]>.60 and hi[2]<1.30:drape[ids]=True
drape=drape[weld]

def smooth(a,b,v):
    t=float(np.clip((v-a)/(b-a),0,1));return t*t*(3-2*t)

# Four anatomical strands, three articulated links per strand. Their roots are
# fixed to the pelvis; the actual long middle strand receives its full length.
centres=[(.087,-.205,1.025),(.176,-.280,.935),(.308,-.285,.640),(.324,-.381,.990)]
chains=[]
for c,(x,y,bottom) in enumerate(centres):
    root=np.array([x,y,1.365]);tip=np.array([x,y,bottom])
    chain=np.array([root*(1-t)+tip*t for t in (0,1/3,2/3,1)])
    chains.append(chain)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for c,chain in enumerate(chains):
    parent=rig.data.edit_bones['Bone_001']
    for j,point in enumerate(chain):
        name='M66_Drape_%02d_%02d'%(c,j);bone=rig.data.edit_bones.new(name)
        bone.head=Vector(point);bone.tail=Vector(chain[j+1] if j<3 else point+np.array([0,0,-.035]))
        bone.parent=parent;bone.use_deform=True;bone.align_roll(Vector((0,1,0)));parent=bone
bpy.ops.object.mode_set(mode='OBJECT')
for c in range(4):
    for j in range(4):mesh.vertex_groups.new(name='M66_Drape_%02d_%02d'%(c,j))

for i in np.flatnonzero(drape):
    x,y,z=pos[i]
    distances=np.array([np.linalg.norm(np.array([x,y])-np.array(centre[:2])) for centre in centres])
    # Below the shared upper tissue, each separated lobe follows its own chain;
    # the root web softly shares adjacent roots to avoid a rigid cut seam.
    width=.025+.055*smooth(1.12,1.32,z)
    influence=np.exp(-(distances-distances.min())/width);influence/=influence.sum()
    flex=1-smooth(1.25,1.36,z)
    target={'Bone_001':1-flex}
    for c,chain in enumerate(chains):
        t=float(np.clip((chain[0,2]-z)/(chain[0,2]-chain[-1,2])*3,0,3))
        a=min(2,int(t));f=t-a
        for j,v in ((a,1-f),(a+1,f)):
            name='M66_Drape_%02d_%02d'%(c,j)
            target[name]=target.get(name,0)+float(influence[c]*v*flex)
    result[i]=target

changed=set(hand_changed)|set(map(int,np.flatnonzero(drape)))
seams={}
for i,k in enumerate(weld):seams.setdefault(int(k),[]).append(i)
for ids in seams.values():
    if len(ids)<2 or not any(i in changed for i in ids):continue
    mean={}
    for i in ids:
        for n,v in result[i].items():mean[n]=mean.get(n,0)+v/len(ids)
    for i in ids:result[i]=dict(mean);changed.add(i)
for i in changed:
    values=sorted(((n,v) for n,v in result[i].items() if v>1e-6),key=lambda x:-x[1])[:8]
    total=sum(v for _,v in values)
    for g in list(mesh.data.vertices[i].groups):mesh.vertex_groups[g.group].remove([i])
    for n,v in values:mesh.vertex_groups[n].add([i],v/total,'REPLACE')

mesh['M66_surface_repair']='V10 full giant-hand anatomical ownership; four pelvis-supported dynamic drape chains'
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/SK_M66_ThumbDrape_V10.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,use_mesh_modifiers=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
rig.animation_data.action=action
if action and action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.context.scene.frame_set(0)
authoring=ROOT/'Authoring/M66_thumb_drape_v10.blend';bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
report={'fbx':str(fbx),'authoring':str(authoring),'hand_repaired_vertices':len(hand_changed),
    'drape_vertices':int(drape.sum()),'edited_vertices':len(changed),'added_bones':16,'bones':len(rig.data.bones),
    'chains':[[p.tolist() for p in chain] for chain in chains],
    'vertices':len(pos),'geometry_modified':False,'uv_modified':False,'animation_modified':False,
    'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/skin_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_THUMB_DRAPE_AUTHORED '+json.dumps({k:report[k] for k in ('hand_repaired_vertices','drape_vertices','edited_vertices','added_bones','bones')}),flush=True)
