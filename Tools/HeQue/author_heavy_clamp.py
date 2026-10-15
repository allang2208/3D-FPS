"""Author the heavy bilateral clamp on the delivered HeQue rig; no mesh edits."""
import bpy, ast, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/HeavyClampV01'
for folder in ('Authoring','Export','Records','Before','Audio'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody']
rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive))
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
desired={};END=4.2;START=1.5;CONTACT_END=1.75;FPS=60
helpers=ast.parse((PROJECT/'Tools/HeQue/author_side_crush.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('ease','curve','transform','at')],type_ignores=[]),'HeQue/clamp_helpers','exec'))

def knee_at(hip,foot,s,pole):
    a=(heads[s['lower']]-heads[s['upper']]).length;b=(heads[s['foot']]-heads[s['lower']]).length
    axis=(foot-hip).normalized();d=min((foot-hip).length,a+b-.001)
    pole=(pole-axis*pole.dot(axis)).normalized();along=(a*a-b*b+d*d)/(2*d)
    return hip+axis*along+pole*math.sqrt(max(0.,a*a-along*along))

def pose(t):
    desired.clear()
    # Feet settle first. The arch sinks and draws back while the fleshy walls
    # open; only the final 0.20s closes them. No turning or target tracking.
    opened=curve(t,[(0,0),(.28,.10),(1.25,1),(1.50,1),(1.70,-.70),(1.80,-.60),(2.55,-.60),(3.35,.12),(END,0)])
    drive=curve(t,[(0,0),(1.25,-.055),(1.50,-.055),(1.70,.49),(1.80,.45),(2.55,.45),(3.50,.12),(END,0)])
    drop=curve(t,[(0,0),(.28,-.035),(1.25,-.17),(1.50,-.18),(1.70,-.41),(1.80,-.45),(2.55,-.43),(3.50,-.12),(END,0)])
    lean=math.radians(curve(t,[(0,0),(1.25,-5),(1.50,-5),(1.70,22),(1.80,24),(2.55,23),(3.50,6),(END,0)]))
    top=heads['HQ_Arch']
    mass=Matrix.Translation(top+Vector((0,-drive,drop)))@Matrix.Rotation(lean,4,'X')@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        sign=-1 if side=='R' else 1
        # The continuous upper arch stays connected, while each half flexes
        # around it. The IK pole draws the lower walls inward to make the clamp.
        spread=Matrix.Translation(top)@Matrix.Rotation(math.radians(-sign*7*opened),4,'Y')@Matrix.Translation(-top)
        half=mass@spread
        for name in s['arch']:transform(name,half)
        hip=half@heads[s['upper']];foot=heads[s['foot']].copy()
        # A small outward brace is placed before the windup, then held through
        # contact and the long exhausted hold; no foot skating during impact.
        brace=curve(t,[(0,0),(.30,1),(3.35,1),(END,0)])
        foot.x+=sign*.035*brace
        foot.z+=.018*math.sin(math.pi*min(1.,t/.30)) if t<.30 else .018*math.sin(math.pi*(t-3.35)/(END-3.35)) if t>3.35 else 0
        pole=Vector((sign*(.65*opened),-1,0))
        knee=knee_at(hip,foot,s,pole)
        at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        foot_matrix=Matrix.Translation(foot-heads[s['foot']])
        for name in (s['foot'],s['toe'],s['tip']):transform(name,foot_matrix)
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    # The suspended core lags the thrust, then swings forward after the walls
    # stop. Recovery opens the middle well before the body can attack again.
    lag=math.radians(curve(t,[(0,0),(1.50,-3),(1.68,-19),(1.92,17),(2.24,-9),(2.62,5),(3.10,-2),(END,0)]))
    cp=heads['HQ_CoreSwing'];core=mass@Matrix.Translation(cp)@Matrix.Rotation(lag,4,'X')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length
        swing=curve(max(0,t-i*.014),[(0,0),(1.50,-.03),(1.70,.55),(1.96,-.65),(2.25,.30),(2.62,-.14),(3.15,.045),(END,0)])
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((swing*.18,swing,0))).normalized()
        if current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            horizontal=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2))
            direction.x=horizontal.x;direction.y=horizontal.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

# Bilateral forward/inner flesh only; the chain and back of the boss do not
# inflict clamp damage. Skin these same vertex bindings again after UE import.
verts=np.array([v.co[:] for v in body.data.vertices])
selected=np.flatnonzero((np.abs(verts[:,0])>.13)&(verts[:,2]>.18)&(verts[:,2]<1.12)&((verts[:,1]<-.10)|(np.abs(verts[:,0])<.32)))
cells={}
for index in selected:
    key=tuple(np.floor(verts[index]/.14).astype(int))
    if key not in cells:cells[key]=int(index)
samples=[]
for index in cells.values():
    v=body.data.vertices[index]
    samples.append((v.co.copy(),[(body.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-5]))
scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(END*FPS)+1
action=bpy.data.actions.new('A_HeQue_HeavyClamp');action.use_fake_user=True;rig.animation_data.action=action
contacts=[]
for f in range(scene.frame_end):
    t=f/FPS;scene.frame_set(f+1);pose(t)
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=f+1,group=b.name)
        b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
        b.keyframe_insert('scale',frame=f+1,group=b.name)
    if START-1/FPS-1e-5<=t<=CONTACT_END+1e-5:
        contacts.append(dict(time=t))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_HeavyClamp.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_HeavyClamp_v01.blend'))
report=dict(clip='A_HeQue_HeavyClamp',duration=END,fps=FPS,contact_start=START,contact_end=CONTACT_END,
    close_seconds=.20,recovery_seconds=END-CONTACT_END,exhausted_hold_end=2.55,root_motion=False,
    damage=85.,cooldown=6.8,trigger_cm=310.,hit_radius_cm=18.,frames=contacts,
    reference_heads={n:list(heads[n]) for n in ('HQ_Root','HQ_Arch','Bone_006','Bone_013')},
    surface_bindings=[dict(position=list(v),weights=weights) for v,weights in samples],surface_samples=len(samples),runtime_tested=False)
(ROOT/'Records/motion.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(PROJECT/'Source/FPSGAME/Monsters/HeQueClampTiming.h').write_text(
    '#pragma once\n// Generated with Tools/HeQue/author_heavy_clamp.py. Native seconds.\nnamespace HeQueClampTiming\n{\n'
    f'    inline constexpr float ContactStart={START:.2f}f;\n    inline constexpr float ContactEnd={CONTACT_END:.2f}f;\n'
    f'    inline constexpr float End={END:.2f}f;\n}}\n',encoding='utf8')
print('HEQUE_HEAVY_CLAMP_AUTHORED '+json.dumps(dict(seconds=END,contact_frames=len(contacts),surface_samples=len(samples))),flush=True)
