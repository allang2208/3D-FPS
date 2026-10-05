"""Re-author M08 collapse above its support plane, retaining the original skin.
Surface fitting is part of the animation bake, not a runtime test or render.
"""
import bpy, ast, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'DeathV10_20261005';OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
SOURCE=BASE/'MotionV09_20261005/M08_Attacks_MotionV09.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
obj=bpy.data.objects['SK_LurkerM08'];rig=bpy.data.objects['Armature'];arm=rig.data
mod=next(m for m in obj.modifiers if m.type=='ARMATURE');mod.show_viewport=False
rig.animation_data_create();rig.animation_data.action=None
NAMES=[b.name for b in arm.bones];PARENT={b.name:b.parent.name if b.parent else None for b in arm.bones}
REST={b.name:b.matrix_local.copy() for b in arm.bones}
LOCAL={n:REST[PARENT[n]].inverted()@REST[n] if PARENT[n] else REST[n].copy() for n in NAMES}
module=ast.parse((PROJECT/'Tools/LurkerM08/author_canine_v03.py').read_text(encoding='utf-8'))
helpers={'fk','world','orient','aim','turn','move_world','ease','two_bone','rest_pole','fit_hock','support_helpers'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<M08 fitted rig adapters>','exec'))
module=ast.parse((PROJECT/'Tools/LurkerM08/author_pounce_v05.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='curve'],type_ignores=[]),'<M08 continuous curves>','exec'))

def two_bone(local,chain,goal,pole):
    """Choose the closest anatomical elbow/knee solution above the floor.
    A fixed world pole can fold the wide forearm underneath a rolling chest.
    Constrain the joint's circle before solving, rather than lifting the corpse.
    """
    w=fk(local);a=w[chain[0]].translation
    l1=(REST[chain[1]].translation-REST[chain[0]].translation).length
    l2=(REST[chain[2]].translation-REST[chain[1]].translation).length
    d=goal-a;axis=d.normalized();reach=max(abs(l1-l2)+.0001,min(d.length,(l1+l2)*.975))
    along=(l1*l1-l2*l2+reach*reach)/(2*reach)
    radius=math.sqrt(max(0.,l1*l1-along*along));center=a+axis*along
    bend=(pole-axis*pole.dot(axis)).normalized()
    up=Vector((0,0,1));up_plane=up-axis*up.dot(axis)
    minimum=.15 if chain[0].startswith('upperarm') else .14
    if up_plane.length>1e-5 and radius>1e-5 and (center+bend*radius).z<minimum:
        vertical=up_plane.normalized()
        amount=max(-1.,min(1.,(minimum-center.z)/(radius*up_plane.length)))
        across=bend-vertical*bend.dot(vertical)
        if across.length<1e-5:across=axis.cross(vertical)
        bend=vertical*amount+across.normalized()*math.sqrt(max(0.,1-amount*amount))
    mid=center+bend*radius
    aim(local,chain[0],mid-a,chain[1]);aim(local,chain[1],a+axis*reach-mid,chain[2])

# Cache the original per-vertex bindings once. Solve the whole skin's lowest
# position, including fingers, oral surface and arch, at every authored frame.
coords=np.empty(len(obj.data.vertices)*3,dtype=np.float64)
obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
members={n:[[],[]] for n in NAMES}
groups={g.index:g.name for g in obj.vertex_groups}
for vertex in obj.data.vertices:
    for influence in vertex.groups:
        name=groups[influence.group]
        if name in members and influence.weight>0:
            members[name][0].append(vertex.index);members[name][1].append(influence.weight)
skin={}
for name,(indices,weights) in members.items():
    if not indices:continue
    ids=np.array(indices,dtype=np.int32);weights=np.array(weights,dtype=np.float64)
    inv=np.array(REST[name].inverted(),dtype=np.float64)
    points=coords[ids]@inv[:3,:3].T+inv[:3,3]
    skin[name]=(ids,weights,points)
floor=float(coords[:,2].min())

def lowest_skin(pose):
    z=np.zeros(len(coords),dtype=np.float64)
    for name,(ids,weights,points) in skin.items():
        row=np.array(pose[name],dtype=np.float64)[2]
        z[ids]+=(points@row[:3]+row[3])*weights
    vertex=int(z.argmin())
    return float(z[vertex]),vertex

# Match the existing central collision capsules at the handoff. No changes
# to the PhysicsAsset or shared corpse solver are made by this revision.
cores=[('pelvis','spine_01',.17),('chest','neck',.18),('neck','head',.15),('head','Wolf_-Head',.19),
       ('arch_front.L','arch_crown',.05),('arch_front.R','arch_crown',.05),
       ('arch_rear.L','arch_crown',.05),('arch_rear.R','arch_crown',.05),('arch_crown',None,.08)]

def lowest_core(pose):
    height=float('inf')
    for name,end,radius in cores:
        offset=REST[name].inverted()@REST[end].translation if end else Vector((0,.12,0))
        center=pose[name]@(offset*.5)
        axis=pose[name].to_3x3()@offset.normalized()
        length=max(0.,offset.length-radius*1.5)
        height=min(height,center.z-abs(axis.z)*length*.5-radius)
    return height

duration=1.4;count=round(duration*120);locals=[];lifts=[];support_keys=[]
for index in range(count+1):
    t=index/120;local={n:m.copy() for n,m in LOCAL.items()}
    fall=curve(t,[(0,0),(.14,.07),(.32,.28),(.58,.73),(.88,1),(duration,1)])
    settle=curve(t,[(0,0),(.59,0),(.79,1),(.96,.65),(1.18,.82),(duration,.82)])
    shift=Vector((.12*fall,.025*fall,-.105*fall-.012*settle))
    local['pelvis'].translation+=REST['root'].inverted().to_3x3()@shift
    turn(local,'pelvis',.90*fall,(0,1,0))
    for name,lag,gain in [('spine_01',.035,.25),('spine_02',.018,.30),('chest',0,.45)]:
        sag=curve(max(0,t-lag),[(0,0),(.20,-.035),(.55,.06),(.76,.085),(1.05,.045),(duration,.045)])
        turn(local,name,sag*gain)
    turn(local,'neck',.035*fall-.018*settle);turn(local,'head',.025*fall-.020*settle)
    turn(local,'jaw',math.radians(-18+8*ease(t/1.1)))
    for side,sign in [('L',1),('R',-1)]:
        for front in (True,False):
            foot=('hand.' if front else 'hindfoot.')+side
            delay=(.12 if side=='R' else .32)+(0 if front else .10)
            release=ease((t-delay)/.42)
            w=fk(local)
            goal=REST[foot].translation.lerp(w[foot].translation,release)
            # Released limbs settle alongside the flank, not through the floor.
            goal.x-=sign*(.035 if front else .025)*release
            goal.z=max(REST[foot].translation.z,goal.z)
            if front:
                move_world(local,'scapula.'+side,Vector((0,.015*release,0)))
                two_bone(local,['upperarm.'+side,'forearm.'+side,foot],goal,rest_pole('upperarm.'+side,'forearm.'+side,foot))
            else:
                fit_hock(local,side,goal,(REST[foot].translation-REST['ankle.'+side].translation).normalized())
            orient(local,foot,REST[foot].to_quaternion().slerp(w[foot].to_quaternion(),release*.35))
            if front:
                for finger in range(1,6):
                    turn(local,f'finger{finger}_01.{side}',math.radians(2.0)*release)
                    turn(local,f'finger{finger}_02.{side}',math.radians(5.0)*release)
    support_helpers(local)
    pose=fk(local)
    skin_height,skin_vertex=lowest_skin(pose)
    skin_lift=max(0.,floor+.012*ease(t/.18)-skin_height)
    core_lift=max(0.,floor+.015-lowest_core(pose))*ease((t-.35)/.32)
    locals.append(local);lifts.append(max(skin_lift,core_lift))
    support_keys.append({'time':t,'skin_lift':skin_lift,'core_lift':core_lift,'support_vertex':skin_vertex})

# A small forward/backward envelope makes changes in the supporting surface
# anticipate contact rather than snapping upward when a new extremum takes over.
smooth_lifts=[max(lifts[j]-.004*abs(j-i) for j in range(max(0,i-5),min(count+1,i+6))) for i in range(count+1)]
action=bpy.data.actions.new('A_M08_Death_DeathV10');action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=1;scene.frame_end=count+1
for index,local in enumerate(locals):
    move_world(local,'pelvis',Vector((0,0,smooth_lifts[index])))
    for name in NAMES:
        pb=rig.pose.bones[name];loc,q,s=(LOCAL[name].inverted()@local[name]).decompose()
        if index>0 and pb.rotation_quaternion.dot(q)<0:q.negate()
        pb.rotation_mode='QUATERNION';pb.location=loc;pb.rotation_quaternion=q;pb.scale=(1,1,1)
        for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=index+1,group=name)

scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
file=ANIM/(action.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_Death_Grounded_V10.blend'))
report={'revision':'M08_DeathV10_20261005','source':str(SOURCE),
    'mesh_asset':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03',
    'clips':{'Death':{'file':str(file),'seconds':duration,'frames':count+1,'contact':[-1,-1]}},
    'source_floor_m':floor,'baked_surface_vertex_count':len(coords),'max_baked_support_lift_m':max(smooth_lifts),
    'death_animation_fraction':.55,'physics_handoff_seconds':.77,
    'largest_support_key':support_keys[int(np.argmax(lifts))],
    'method':'Ground-constrained collapse; exact original skin height and existing central capsule clearance used during authoring',
    'runtime_tested':False,'preview_rendered':False}
(OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_DEATH_V10_AUTHORING_SAVED',flush=True)
