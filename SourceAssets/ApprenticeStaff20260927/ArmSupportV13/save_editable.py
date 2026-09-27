"""Save native skin, full arm pose library and editable staff action takes.
Background authoring only. No preview, rendering, editor launch or runtime test.
The game samples the identical complete local pose table compiled into C++.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
data=json.loads((P/'full-pose.json').read_text())
skin=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json').read_text())
rest={n:Matrix(m) for n,m in data['rest'].items()};parent=dict(data['parent']);order=list(rest)
S=Matrix.Diagonal((1,-1,1));FPS=120
def mat(q,p):
    m=q.to_4x4();m.translation=Vector(p);return m
def convert(m):return mat(S@m.to_3x3()@S,S@m.translation*.01)
def mix(a,b,u):return mat(a.to_quaternion().slerp(b.to_quaternion(),u).to_matrix(),a.translation.lerp(b.translation,u))
def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def rotation_zx(v):
    z=Vector(v).normalized();x=Vector((1,0,0));x=(x-z*x.dot(z)).normalized();return Matrix((x,z.cross(x),z)).transposed()

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.render.fps=FPS
arm=bpy.data.armatures.new('Staff_V7_BowGrasp_V13');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
parent['staff_grip']='hand_r';rest['staff_grip']=rest['hand_r']@Matrix(data['variants']['false']['hand']).inverted();order.append('staff_grip')
for n in order:
    b=arm.edit_bones.new(n);b.head=(0,0,0);b.tail=(0,.025,0);b.matrix=convert(rest[n]);b.length=.025
    if parent[n]:b.parent=arm.edit_bones[parent[n]]
bpy.ops.object.mode_set(mode='OBJECT')
mesh=bpy.data.meshes.new('BarePalmV7_OriginalSurface');mesh.from_pydata([S@Vector(p)*.01 for p in skin['positions']],[],skin['triangles']);mesh.update()
obj=bpy.data.objects.new('Staff_V7_Arms',mesh);bpy.context.collection.objects.link(obj);obj.parent=rig
mod=obj.modifiers.new('NativeSkin','ARMATURE');mod.object=rig
for n in {n for w in skin['weights'] for n in w}:obj.vertex_groups.new(name=n)
for i,w in enumerate(skin['weights']):
    for n,v in w.items():obj.vertex_groups[n].add([i],v,'REPLACE')
for label in ('BareUpperArms','BareLowerArms','BareHandsOriginalGrip'):
    m=bpy.data.materials.new(label);m.diffuse_color=(.372,.232,.182,1);mesh.materials.append(m)
uvs=[mesh.uv_layers.new(name=n) for n in ('Anatomy','CanonicalXY','CanonicalZNormalX','CanonicalNormalYZ')];normals=[]
for poly in mesh.polygons:
    ti=poly.index;poly.material_index=skin['triangle_materials'][ti];poly.use_smooth=True
    for j,loop in enumerate(poly.loop_indices):
        vi=mesh.loops[loop].vertex_index;c=skin['canonical_positions'][vi];n=skin['canonical_normals'][ti][j]
        for layer,pair in zip(uvs,[skin['uv'][ti][j],c[:2],(c[2],n[0]),n[1:]]):layer.data[loop].uv=(pair[0],1-pair[1])
        normals.append(S@Vector(skin['normals'][ti][j]))
mesh.normals_split_custom_set(normals)
rig.animation_data_create()

def key_pose(action,frame,world,previous):
    for n in order:
        b=rig.pose.bones[n];par=parent[n]
        relative=convert(world[par]).inverted()@convert(world[n]) if par else convert(world[n])
        restlocal=arm.bones[par].matrix_local.inverted()@arm.bones[n].matrix_local if par else arm.bones[n].matrix_local
        b.rotation_mode='QUATERNION';b.matrix_basis=restlocal.inverted()@relative
        if n in previous and b.rotation_quaternion.dot(previous[n])<0:b.rotation_quaternion.negate()
        previous[n]=b.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=frame)

def full_world(variant,index):
    clip=data['poses'][variant][index];w={n:m.copy() for n,m in rest.items()}
    w.update({n:Matrix(m) for n,m in clip['component'].items()});w['staff_grip']=Matrix(clip['contact']);return w
for variant,clips in data['poses'].items():
    for i,clip in enumerate(clips):
        action=bpy.data.actions.new('Pose_Staff_'+variant+'_'+clip['name']);action.use_fake_user=True;rig.animation_data.action=action
        key_pose(action,0,full_world(variant,i),{})

# Editable full-chain action takes. Contact trajectories and phase durations
# match StaffCastMotion.h; the runtime also adds player-dependent locomotion.
clips=data['poses']['false'];locals_=[{n:Matrix(m) for n,m in clip['local'].items()} for clip in clips]
contacts=[Matrix(c['contact']) for c in clips];hand=Matrix(data['variants']['false']['hand'])
def trajectory(role,t,duration):
    u=ease(t/duration);w=[0.]*6
    if role=='Raise':
        a,b=0,1;contact=mix(contacts[a],contacts[b],u);contact.translation+=Vector((-3,2,1))*(16*u*u*(1-u)*(1-u))
    elif role=='Release':
        if t<.035:a,b,u=1,2,ease(t/.035)
        elif t<.18:a,b,u=2,3,ease((t-.035)/.145)
        else:a,b,u=3,4,ease((t-.18)/.10)
        contact=mix(contacts[a],contacts[b],u)
    elif role=='Recover':
        a,b=4,0;contact=mix(contacts[a],contacts[b],u);contact.translation+=Vector((0,2,2))*(16*u*u*(1-u)*(1-u))
    else:
        a=b=5 if role=='Run' else 0;contact=contacts[a].copy()
        if role=='Equip':contact.translation.z-=35*(1-min(1,t/.35))**2
        elif role in ('Walk','Run'):
            phase=t/duration*math.tau;run=role=='Run'
            contact.translation+=Vector((2.5*math.sin(phase) if run else .55*math.sin(2*phase-.3), (1.65 if run else 1.05)*math.cos(phase),-(.95 if run else .48)*(math.cos(2*phase)+.1*math.cos(4*phase))))
        elif role=='Idle':contact.translation+=Vector((0,.06*math.sin(t*1.7),.14*math.sin(t*1.9)))
    w[a]+=1-u;w[b]+=u;return w,contact
def sample(weights,contact):
    w={n:m.copy() for n,m in rest.items()}
    for n in data['order']:
        total=0.;local=None
        for i,weight in enumerate(weights):
            if weight<=0:continue
            local=locals_[i][n].copy() if local is None else mix(local,locals_[i][n],weight/(total+weight));total+=weight
        w[n]=w[parent[n]]@local
    goal=contact@hand;transport=goal@w['hand_r'].inverted()
    for n in data['order']:
        if n.endswith('_r'):w[n]=transport@w[n]
    w['staff_grip']=contact;return w
for role,duration in [('Idle',2.),('Walk',1.),('Run',.7),('Raise',.2),('Release',.28),('Recover',.42),('Equip',.35)]:
    action=bpy.data.actions.new('A_Staff_'+role+'_V13');action.use_fake_user=True;rig.animation_data.action=action;previous={}
    for f in range(round(duration*FPS)+1):
        weights,contact=trajectory(role,f/FPS,duration);key_pose(action,f,sample(weights,contact),previous)

# Preserve the actual modular staff geometry as an editable contact reference.
with bpy.data.libraries.load(str(P.parent/'apprentice_staff_modular.blend'),link=False) as (source,target):
    target.objects=[n for n in source.objects if n in ('SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false')]
mount=bpy.data.objects.new('Staff_Contact',None);bpy.context.collection.objects.link(mount)
constraint=mount.constraints.new('COPY_TRANSFORMS');constraint.target=rig;constraint.subtarget='staff_grip'
for staff in target.objects:
    bpy.context.collection.objects.link(staff);staff.parent=mount
    for v in staff.data.vertices:v.co=(v.co-Vector((0,0,32)))*.01
rig.animation_data.action=bpy.data.actions['A_Staff_Idle_V13'];scene.frame_start=0;scene.frame_end=240;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Staff_BowBasedGrip_V13.blend'))
(P/'editable-source.json').write_text(json.dumps({'revision':13,'source':'Staff_BowBasedGrip_V13.blend','full_pose_count':24,
    'action_takes':['Idle','Walk','Run','Raise','Release','Recover','Equip'],'fps':FPS,
    'runtime':'compiled StaffAuthoredPoseV13.h full local pose table; shared phase clock; player-dependent additive movement',
    'ue_asset_import_required':False,'rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('STAFF_V13_EDITABLE_SOURCE_SAVED',flush=True)
