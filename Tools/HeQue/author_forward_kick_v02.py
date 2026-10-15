"""Replace SideCrush presentation with a planted, football-style forward kick."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SideCrushV02'
for folder in ('Authoring','Export','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody']
rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive))
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides'];desired={}
END=3.2;START=1.25;CONTACT_END=1.55;FPS=60
helpers=ast.parse((PROJECT/'Tools/HeQue/author_side_crush.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('transform','at')],type_ignores=[]),'HeQue/kick_helpers','exec'))

def track(t,keys):
    """Monotone Hermite: carry velocity through intermediate poses, stop at reversals."""
    if t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    h=[b[0]-a[0] for a,b in zip(keys[:-1],keys[1:])]
    d=[(b[1]-a[1])/dt for a,b,dt in zip(keys[:-1],keys[1:],h)]
    m=[0.]*len(keys)
    for i in range(1,len(keys)-1):
        if d[i-1]*d[i]>0:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
            m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    i=next(i for i in range(len(h)) if t<=keys[i+1][0]);u=(t-keys[i][0])/h[i]
    return (2*u**3-3*u*u+1)*keys[i][1]+(u**3-2*u*u+u)*h[i]*m[i]+(-2*u**3+3*u*u)*keys[i+1][1]+(u**3-u*u)*h[i]*m[i+1]

def solve(hip,foot,s,pole):
    a=(heads[s['lower']]-heads[s['upper']]).length;b=(heads[s['foot']]-heads[s['lower']]).length
    delta=foot-hip;axis=delta.normalized();d=min(delta.length,a+b-.001)
    pole=(pole-axis*pole.dot(axis)).normalized();along=(a*a-b*b+d*d)/(2*d)
    return hip+axis*along+pole*math.sqrt(max(0.,a*a-along*along))

def pose(t):
    desired.clear()
    # Transfer weight over the right support before the left foot leaves.
    # Pelvis opens only slightly; the kick travels forward instead of revolving
    # the complete leg around a 110-degree body pivot.
    sx=track(t,[(0,0),(.32,-.125),(.85,-.17),(1.3,-.15),(1.65,-.17),(2.25,-.13),(2.75,-.035),(END,0)])
    sy=track(t,[(0,0),(.65,.025),(1.02,.045),(1.32,-.12),(1.55,-.155),(2.10,-.07),(2.75,0),(END,0)])
    sz=track(t,[(0,0),(.35,-.055),(.95,-.085),(1.32,-.035),(1.55,-.045),(2.30,-.06),(2.70,-.065),(2.80,-.085),(END,0)])
    yaw=math.radians(track(t,[(0,0),(.95,9),(1.1,7),(1.36,-7),(1.65,-9),(2.4,-3),(END,0)]))
    roll=math.radians(track(t,[(0,0),(.40,-5),(.95,-7),(1.35,-4),(1.70,-7),(2.6,-2),(END,0)]))
    pitch=math.radians(track(t,[(0,0),(.85,-3),(1.10,-5),(1.38,5),(1.7,8),(2.35,3),(END,0)]))
    top=heads['HQ_Arch'];mass=Matrix.Translation(top+Vector((sx,sy,sz)))@Matrix.Rotation(yaw,4,'Z')@Matrix.Rotation(roll,4,'Y')@Matrix.Rotation(pitch,4,'X')@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        for name in s['arch']:transform(name,mass)
        hip=mass@heads[s['upper']]
        if side=='R':
            foot=heads[s['foot']].copy();knee=solve(hip,foot,s,Vector((-.04,-1,0)))
            foot_matrix=Matrix.Identity(4)
        else:
            upper=heads[s['lower']]-heads[s['upper']];lower=heads[s['foot']]-heads[s['lower']]
            base=math.degrees(math.atan2(upper.y,-upper.z))
            flex=math.degrees(math.atan2(lower.y,-lower.z))-base
            # Hip leads; the bent lower limb trails, then extends very quickly.
            # A folded return is a separate path, not a reversed kick.
            thigh=math.radians(track(t,[(0,base),(.28,base),(.84,27),(1.06,22),(1.20,-17),(1.36,-53),(1.53,-62),(1.76,-53),(2.12,-31),(2.55,-9),(2.75,base),(END,base)]))
            bend=math.radians(track(t,[(0,flex),(.28,flex),(.82,103),(1.08,101),(1.21,77),(1.36,24),(1.53,16),(1.78,53),(2.12,88),(2.55,37),(2.75,flex),(END,flex)]))
            lateral=track(t,[(0,upper.x),(.82,.07),(1.10,.045),(1.34,-.045),(1.60,-.045),(2.20,.01),(2.75,upper.x),(END,upper.x)])
            length=math.sqrt(max(0.,upper.length**2-lateral**2))
            fk_knee=hip+Vector((lateral,length*math.sin(thigh),-length*math.cos(thigh)))
            fk_foot=fk_knee+Vector((lower.x,math.sqrt(lower.length**2-lower.x**2)*math.sin(thigh+bend),-math.sqrt(lower.length**2-lower.x**2)*math.cos(thigh+bend)))
            airborne=track(t,[(0,0),(.28,0),(.52,1),(2.12,1),(2.70,0),(END,0)])
            foot=heads[s['foot']].lerp(fk_foot,airborne)
            knee=solve(hip,foot,s,fk_knee-hip)
            ankle=math.radians(track(t,[(0,0),(.38,0),(.90,38),(1.12,26),(1.36,13),(1.53,5),(1.90,18),(2.35,6),(2.70,0),(END,0)]))*airborne
            foot_matrix=Matrix.Translation(foot)@Matrix.Rotation(ankle,4,'X')@Matrix.Translation(-heads[s['foot']])
        at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        for name in (s['foot'],s['toe'],s['tip']):transform(name,foot_matrix)
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    # Soft mass and hardware respond after the torso, with decaying follow-through.
    lag=math.radians(track(t,[(0,0),(.9,-6),(1.22,8),(1.53,-13),(1.9,7),(2.25,-4),(2.7,2),(END,0)]))
    lateral=math.radians(track(t,[(0,0),(.55,5),(1.14,3),(1.55,-6),(1.95,3),(2.45,-1),(END,0)]))
    cp=heads['HQ_CoreSwing'];core=mass@Matrix.Translation(cp)@Matrix.Rotation(lag,4,'X')@Matrix.Rotation(lateral,4,'Y')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length;delayed=max(0,t-i*.017)
        swing=track(delayed,[(0,0),(.9,-.065),(1.20,.14),(1.57,-.26),(1.94,.14),(2.32,-.065),(2.73,.03),(END,0)])
        side_swing=track(delayed,[(0,0),(.75,-.08),(1.40,.11),(1.85,-.06),(2.4,.03),(END,0)])
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((side_swing,swing,0))).normalized()
        if current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            xy=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2))
            direction.x=xy.x;direction.y=xy.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

# Only the striking left foot / lower wall. Neither the support leg nor the
# high arch inherits an invisible old sweeping sector.
verts=np.array([v.co[:] for v in body.data.vertices])
selected=np.flatnonzero((verts[:,0]>.13)&(verts[:,2]<.80)&(verts[:,2]>.035))
cells={}
for index in selected:
    key=tuple(np.floor(verts[index]/.14).astype(int))
    if key not in cells:cells[key]=int(index)
samples=[]
for index in cells.values():
    v=body.data.vertices[index]
    samples.append((v.co.copy(),[(body.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-5]))
scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(END*FPS)+1
action=bpy.data.actions.new('A_HeQue_ForwardKickV02');action.use_fake_user=True;rig.animation_data.action=action
contacts=[]
for f in range(scene.frame_end):
    t=f/FPS;scene.frame_set(f+1);pose(t)
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=f+1,group=b.name)
        b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
        b.keyframe_insert('scale',frame=f+1,group=b.name)
    if START-1e-5<=t<=CONTACT_END+1e-5:contacts.append(dict(time=t))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_ForwardKickV02.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_ForwardKick_v02.blend'))
report=dict(clip='A_HeQue_ForwardKickV02',duration=END,fps=FPS,contact_start=START,contact_end=CONTACT_END,
    support_side='R',striking_side='L',direction='forward -Y in source / actor +X in game',root_motion=False,
    frames=contacts,reference_heads={n:list(heads[n]) for n in ('HQ_Root','HQ_Arch','Bone_006','Bone_013')},
    surface_bindings=[dict(position=list(v),weights=weights) for v,weights in samples],surface_samples=len(samples),
    damage=60.,cooldown=4.6,trigger_cm=355.,stop_cm=280.,hit_radius_cm=20.,runtime_tested=False,visual_tested=False,
    key_phases=dict(weight_transfer=[0,.32],backswing=[.32,1.10],hip_leads_knee=[1.10,1.36],follow_through=[1.36,1.55],
        folded_recovery=[1.55,2.70],landing_settle=[2.70,END]))
(ROOT/'Records/motion.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_FORWARD_KICK_AUTHORED '+json.dumps(dict(duration=END,contact_frames=len(contacts),surface_samples=len(samples))),flush=True)
