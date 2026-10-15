"""Author the living HeQue recoil, folded landing and staged supported recovery.

Original animation on the delivered rig; no corpse simulation or mesh rebinding.
The body floor offset is solved from its skinned surface during production.
The articulated chain is baked offline and cannot apply forces to the body.
"""
import ast, bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/KnockdownV02'
for name in ('Authoring','Export','Records','Before'):(ROOT/name).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody']
rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones}
bone_order=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
helpers=ast.parse((PROJECT/'Tools/HeQue/author_rig_motion.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('smooth','clear','at','transform','solve_two')],type_ignores=[]),'HeQue/reaction_helpers','exec'))
FPS=120;DT=1/FPS
AIR=1.2;LAND=.95;RISE=3.

def curve(t,keys):
    for (a,x),(b,y) in zip(keys[:-1],keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]

# Exact weighted surface heights, used as a production support solver rather
# than moving the actor or applying a second root-motion trajectory at runtime.
points=np.array([v.co[:] for v in body.data.vertices],dtype=np.float64)
weights={b.name:[] for b in rig.data.bones}
for v in body.data.vertices:
    for g in v.groups:
        name=body.vertex_groups[g.group].name
        if name in weights and g.weight>0:weights[name].append((v.index,g.weight))
skin=[]
for name,rows in weights.items():
    if rows:
        index=np.array([r[0] for r in rows]);w=np.array([r[1] for r in rows])
        skin.append((name,index,w,points[index]))
bind_floor=float(points[:,2].min())

def floor_body():
    z=np.zeros(len(points))
    for name,index,w,p in skin:
        m=np.array(desired[name]@rest[name].inverted())
        z[index]+=w*(p@m[2,:3]+m[2,3])
    return float(z.min())

def body_pose(role,t):
    clear()
    if role=='Air':
        sink=curve(t,[(0,0),(.12,-.025),(.36,-.11),(.75,-.13),(AIR,-.12)])
        lean=curve(t,[(0,0),(.12,-17),(.36,-12),(.75,-4),(AIR,6)])
        lateral=curve(t,[(0,0),(.15,3.5),(.36,1.5),(.75,-1),(AIR,0)])
        travel=curve(t,[(0,0),(.20,.02),(.75,0),(AIR,0)])
        feet={s:(curve(t,[(0,0),(.36,.09),(AIR,.03)]),curve(t,[(0,0),(.36,.14),(AIR,.07)]),
            curve(t,[(0,0),(.36,18),(AIR,8)])) for s in sides}
        core_angle=curve(t,[(0,0),(.18,13),(.42,-8),(.80,5),(AIR,0)])
    elif role=='Land':
        # First frame matches the terminal airborne pose. Fast joint folding
        # absorbs the contact, followed by a small, slow residual settlement.
        sink=curve(t,[(0,-.12),(.08,-.20),(.30,-.86),(.41,-1.03),(.64,-.96),(LAND,-.95)])
        lean=curve(t,[(0,6),(.08,12),(.30,57),(.41,70),(.66,66),(LAND,65)])
        lateral=curve(t,[(0,0),(.30,4),(.46,2),(LAND,2)])
        travel=curve(t,[(0,0),(.30,-.26),(.50,-.29),(LAND,-.28)])
        feet={s:(curve(t,[(0,.03),(.16,.03),(.36,.24 if s=='R' else .18),(LAND,.24 if s=='R' else .18)]),
            curve(t,[(0,.07),(.10,0),(LAND,0)]),curve(t,[(0,8),(.12,0),(LAND,0)])) for s in sides}
        core_angle=curve(t,[(0,0),(.20,-15),(.39,20),(.58,-8),(.78,3),(LAND,0)])
    else:
        # Preparation, right buttress, left buttress, two distinct heavy pushes,
        # then a soft standing settle. This is not reversed landing footage.
        sink=curve(t,[(0,-.95),(.38,-.98),(.72,-.88),(1.22,-.57),(1.55,-.31),
            (1.78,-.34),(2.32,-.035),(2.57,-.055),(RISE,0)])
        lean=curve(t,[(0,65),(.38,67),(.72,57),(1.22,36),(1.55,20),(1.78,23),(2.32,4),(RISE,0)])
        lateral=curve(t,[(0,2),(.38,4),(.72,5),(1.22,-4),(1.55,-2),(2.32,1),(RISE,0)])
        travel=curve(t,[(0,-.28),(.38,-.29),(.72,-.25),(1.22,-.13),(1.78,-.07),(2.50,0),(RISE,0)])
        feet={
            'R':(curve(t,[(0,.24),(.38,.24),(.78,0),(RISE,0)]),curve(t,[(0,0),(.38,0),(.56,.10),(.78,0),(RISE,0)]),0),
            'L':(curve(t,[(0,.18),(.84,.18),(1.27,0),(RISE,0)]),curve(t,[(0,0),(.84,0),(1.04,.10),(1.27,0),(RISE,0)]),0)}
        core_angle=curve(t,[(0,0),(.45,4),(.94,-7),(1.38,9),(1.78,-6),(2.40,5),(2.67,-2),(RISE,0)])
    pivot=heads['HQ_Arch']
    mass=Matrix.Translation(pivot+Vector((0,travel,sink)))@Matrix.Rotation(math.radians(lean),4,'X')@Matrix.Rotation(math.radians(lateral),4,'Y')@Matrix.Translation(-pivot)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        for name in s['arch']:transform(name,mass)
        hip=mass@heads[s['upper']];foot=heads[s['foot']].copy()
        y,z,pitch=feet[side];foot+=Vector((0,y,z))
        knee=solve_two(hip,foot,s)
        at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        sole=Matrix.Translation(foot)@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation(-heads[s['foot']])
        for name in (s['foot'],s['toe'],s['tip']):transform(name,sole)
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    cp=heads['HQ_CoreSwing']
    core=mass@Matrix.Translation(cp)@Matrix.Rotation(math.radians(core_angle),4,'X')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    # Airborne displacement is owned only by CharacterMovement. Ground support
    # comes in over the first contact, not a reference-mesh bounding-box spin.
    support=0 if role=='Air' else smooth(t/.10) if role=='Land' else 1
    dz=max(0.,bind_floor-floor_body())*support
    correction=Matrix.Translation((0,0,dz))
    for name in list(desired):
        if name!='HQ_Root':desired[name]=correction@desired[name]
    return dz

lengths=[(tails[f'HQ_Chain_{i:02d}']-heads[f'HQ_Chain_{i:02d}']).length for i in range(15)]
chain_pos=None;chain_old=None

def chain_pose(grounded):
    global chain_pos,chain_old
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();anchor=cuff@heads['HQ_Chain_00']
    if chain_pos is None:
        chain_pos=[anchor.copy()]
        for length in lengths:chain_pos.append(chain_pos[-1]+Vector((-.006,.002,-.0355)).normalized()*length)
        chain_old=[v.copy() for v in chain_pos]
    previous=[v.copy() for v in chain_pos]
    for i in range(1,16):chain_pos[i]+=(chain_pos[i]-chain_old[i])*.975+Vector((0,0,-9.81*DT*DT))
    # Kinematic anchor plus constrained, fixed-length articulated links. The
    # generated motion is animation data, with no runtime rigid-chain impulses.
    floor=bind_floor+.018
    for iteration in range(32):
        chain_pos[0]=anchor.copy()
        for i,length in enumerate(lengths):
            delta=chain_pos[i+1]-chain_pos[i];distance=delta.length
            if distance<1e-8:continue
            correction=delta*(1-length/distance)
            if i==0:chain_pos[i+1]-=correction
            else:chain_pos[i]+=correction*.5;chain_pos[i+1]-=correction*.5
        if grounded:
            for i in range(1,16):
                if chain_pos[i].z<floor:chain_pos[i].z=floor
    # Resolve from the anchor with exact segment lengths; floor contact limits
    # vertical direction instead of stretching bones to separated solver nodes.
    current=anchor.copy();chain_pos[0]=current.copy()
    for i,length in enumerate(lengths):
        direction=(chain_pos[i+1]-current).normalized()
        if direction.length_squared<.5:direction=Vector((-.2,.1,-1)).normalized()
        if grounded and current.z+direction.z*length<floor:
            direction.z=max(-1.,min(1.,(floor-current.z)/length))
            horizontal=Vector((direction.x,direction.y,0))
            if horizontal.length_squared<1e-8:horizontal=Vector((-.9,.3,0))
            horizontal.normalize();horizontal*=math.sqrt(max(0.,1-direction.z*direction.z))
            direction.x=horizontal.x;direction.y=horizontal.y
        target=current+direction*length
        at(f'HQ_Chain_{i:02d}',current,target);chain_pos[i+1]=target.copy();current=target
    chain_old=previous
    if grounded:
        for i in range(1,16):
            if chain_pos[i].z<=floor+.003:chain_old[i]=chain_old[i].lerp(chain_pos[i],.40)

def resolve():
    for b in bone_order:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        pose=rig.pose.bones[b.name];pose.matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=FPS
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
clips=[]
for role,duration in (('Air',AIR),('Land',LAND),('GetUp',RISE)):
    name='A_HeQue_'+role+'_WeightV02'
    action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*FPS)+1
    offsets=[]
    for f in range(scene.frame_end):
        t=f/FPS;scene.frame_set(f+1);offsets.append(body_pose(role,t))
        # Consecutive clips share the exact endpoint including chain pose.
        if f>0 or role=='Air':chain_pose(role!='Air')
        else:
            for i in range(15):at(f'HQ_Chain_{i:02d}',chain_pos[i],chain_pos[i+1])
        resolve()
        for b in rig.pose.bones:
            b.keyframe_insert('location',frame=f+1,group=b.name)
            b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
            b.keyframe_insert('scale',frame=f+1,group=b.name)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips.append(dict(role=role,name=name,duration=duration,support_lift_max_source_m=max(offsets)))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_knockdown_recovery_v02.blend'))
report=dict(clips=clips,fps=FPS,minimum_down_dwell=.25,source='Original HeQue animation on delivered RigV01',
    surface_support='weighted body surface; fixed-length baked articulated chain',
    airborne_clock='initial 0.36 seconds, then vertical-velocity descent phase',
    recovery_phases=dict(prepare=[0,.38],right_support=[.38,.78],left_support=[.84,1.27],
        first_push=[.72,1.55],effort_pause=[1.55,1.78],second_push=[1.78,2.32],settle=[2.32,3.]),
    gameplay_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HEQUE_KNOCKDOWN_V02_AUTHORED '+json.dumps(report),flush=True)
