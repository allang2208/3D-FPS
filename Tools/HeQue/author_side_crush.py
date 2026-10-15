"""Author HeQue's planted-right-foot side crush on the delivered rig (no mesh edits)."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SideCrushV01'
for folder in ('Authoring','Export','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody']
rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive))
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
desired={};END=3.2;START=1.10;CONTACT_END=1.55;FPS=60

def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)

def curve(t,keys):
    for (a,x),(b,y) in zip(keys[:-1],keys[1:]):
        if t<=b:return x+(y-x)*ease((t-a)/(b-a))
    return keys[-1][1]

def transform(name,m):desired[name]=m@rest[name]

def at(name,head,tail):
    q=(tails[name]-heads[name]).rotation_difference(tail-head)
    desired[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()

def solve(hip,foot,s,yaw):
    a=(heads[s['lower']]-heads[s['upper']]).length;b=(heads[s['foot']]-heads[s['lower']]).length
    v=foot-hip;d=min(v.length,a+b-.001);axis=v.normalized()
    pole=Matrix.Rotation(yaw,3,'Z')@Vector((0,-1,0));pole=(pole-axis*pole.dot(axis)).normalized()
    along=(a*a-b*b+d*d)/(2*d)
    return hip+axis*along+pole*math.sqrt(max(0.,a*a-along*along))

def pose(t):
    desired.clear()
    # Slow load, brief compression, explosive release, recoil, planted pause,
    # then a higher, deliberately slower recovery step with no damage window.
    yaw=math.radians(curve(t,[(0,0),(.65,14),(1.10,22),(1.48,-110),(1.68,-116),(2.0,-110),(2.95,0),(END,0)]))
    tilt=math.radians(curve(t,[(0,0),(.8,-9),(1.10,-12),(1.43,-7),(1.68,-5),(2.1,-4),(3.05,0),(END,0)]))
    squat=curve(t,[(0,0),(.8,-.055),(1.10,-.075),(1.35,-.025),(1.62,-.065),(2.05,-.065),(3.05,0),(END,0)])
    span=curve(t,[(0,0),(.8,.08),(1.1,.14),(1.5,.14),(1.95,.08),(3.,0),(END,0)])
    lift=curve(t,[(0,0),(.45,0),(.95,.11),(1.1,.11),(1.4,.05),(1.6,0),(1.95,0),(2.35,.13),(2.9,0),(END,0)])
    pivot=heads[sides['R']['foot']]
    turn=Matrix.Rotation(yaw,4,'Z')
    mass=Matrix.Translation(pivot+Vector((0,0,squat)))@turn@Matrix.Rotation(tilt,4,'Y')@Matrix.Translation(-pivot)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        for name in s['arch']:transform(name,mass)
        hip=mass@heads[s['upper']]
        if side=='R':foot=pivot.copy()
        else:
            v=heads[s['foot']]-pivot+Vector((span,0,0))
            foot=pivot+turn.to_3x3()@v;foot.z+=lift
        knee=solve(hip,foot,s,yaw)
        at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        foot_matrix=Matrix.Translation(foot)@turn@Matrix.Translation(-heads[s['foot']])
        for name in (s['foot'],s['toe'],s['tip']):transform(name,foot_matrix)
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    # The suspended organ trails the turn, then overshoots after the heavy body stops.
    lag=math.radians(curve(t,[(0,0),(1.1,6),(1.38,-15),(1.62,12),(1.95,-6),(2.4,3),(END,0)]))
    cp=heads['HQ_CoreSwing'];core=mass@Matrix.Translation(cp)@Matrix.Rotation(lag,4,'Y')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted()
    current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length
        delay=i*.017
        swing=curve(max(0,t-delay),[(0,0),(.9,-.035),(1.1,-.055),(1.48,.30),(1.72,.34),(2.02,-.13),(2.42,.075),(2.8,-.025),(END,0)])
        direction=Vector((-.006,.002,-.0355)).normalized()+turn.to_3x3()@Vector((swing,.45*swing,0))
        direction.normalize()
        # Pivot-connected rigid links retain length; their tail turns onto the floor.
        if current.z+direction.z*length<.025:
            direction.z=max(-.2,min(.5,(.025-current.z)/length))
            direction.x=-math.sqrt(max(.01,1-direction.z*direction.z))*.92
            direction.y=.38;direction.normalize()
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

# Sample the actual lower left body surface for damage geometry. Keep one
# representative per small surface voxel, not an oversized invisible sector.
verts=np.array([v.co[:] for v in body.data.vertices])
selected=np.flatnonzero((verts[:,0]>.13)&(verts[:,2]<1.03)&(verts[:,2]>.035))
cells={}
for index in selected:
    key=tuple(np.floor(verts[index]/.16).astype(int))
    if key not in cells:cells[key]=int(index)
samples=[]
for index in cells.values():
    v=body.data.vertices[index]
    weights=[(body.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-5]
    samples.append((v.co.copy(),weights))

scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(END*FPS)+1
action=bpy.data.actions.new('A_HeQue_SideCrush');action.use_fake_user=True;rig.animation_data.action=action
contacts=[]
for f in range(scene.frame_end):
    t=f/FPS;scene.frame_set(f+1);pose(t)
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=f+1,group=b.name)
        b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
        b.keyframe_insert('scale',frame=f+1,group=b.name)
    if START-1e-5<=t<=CONTACT_END+1e-5:
        points=[]
        for v,weights in samples:
            skinned=Vector()
            for name,weight in weights:skinned+=(desired[name]@rest[name].inverted()@v)*weight
            points.append(list(skinned))
        contacts.append(dict(time=t,points=points))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_SideCrush.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_SideCrush_v01.blend'))
report=dict(clip='A_HeQue_SideCrush',duration=END,fps=FPS,contact_start=START,contact_end=CONTACT_END,
    support_side='R',sweeping_side='L',root_motion=False,damage=60.,cooldown=4.6,trigger_cm=355.,stop_cm=280.,
    hit_radius_cm=20.,frames=contacts,reference_heads={n:list(heads[n]) for n in ('HQ_Root','HQ_Arch','Bone_006','Bone_013')},
    surface_bindings=[dict(position=list(v),weights=weights) for v,weights in samples],
    surface_samples=len(samples),source=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'),runtime_tested=False)
(ROOT/'Records/motion.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(PROJECT/'Source/FPSGAME/Monsters/HeQueSweepTiming.h').write_text(
    '#pragma once\n// Generated with Tools/HeQue/author_side_crush.py. Seconds, at native playback rate.\n'
    'namespace HeQueSweepTiming\n{\n'
    f'    inline constexpr float ContactStart={START:.2f}f;\n'
    f'    inline constexpr float ContactEnd={CONTACT_END:.2f}f;\n'
    f'    inline constexpr float End={END:.2f}f;\n}}\n',encoding='utf8')
print('HEQUE_SIDE_CRUSH_AUTHORED '+json.dumps(dict(seconds=END,contact_frames=len(contacts),surface_samples=len(samples))),flush=True)
