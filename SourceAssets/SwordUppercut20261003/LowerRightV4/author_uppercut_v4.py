"""User-directed V4: lower-right offscreen, fast upward cut in the idle grip.

Carry the CURRENT full idle pose as a rigid group. No new wrist, elbow, finger,
blade roll or skinning rotations are introduced. The first-person presentation
offset is baked into native root keys; it is not a player capsule displacement.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P=Path(__file__).parent
ROOT=P.parents[2]
DATA=json.loads((P/'inputs.json').read_text(encoding='utf-8'))
SOURCE=ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
FPS,END=120,1.20
C=Matrix.Diagonal(Vector((1,-1,1)))
NAMES=list(DATA['parents'])

def canonical(row):
    return Matrix.LocRotScale(C@Vector(row['p'])*.01,
        (C@Quaternion(row['q']).to_matrix()@C).to_quaternion(),Vector((1,1,1)))

def smooth(x):
    x=max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

def pose_matrix(p,q):
    return Matrix.LocRotScale(p,q,Vector((1,1,1)))

def lower_right_offset(idle):
    # Author the hidden key against the game's 75-degree vertical, 16:9 frame.
    # Keep a margin for the arm surface and longer modular blade silhouettes.
    half_width=math.tan(math.radians(75)*.5)*(16/9)
    depth=-.22
    points=[m.translation for m in idle.values()]
    base=idle['Blade_Base'].translation
    points.append(base+(idle['Blade_Tip'].translation-base)*1.35)
    right=max(.62,max(max(0.,p.y+depth)*half_width-p.x+.12 for p in points))
    return Vector((right,depth,-.50))

def offset_at(t,hidden):
    top=Vector((.03,.045,.225))
    carry=Vector((.03,.045,.25))
    if t<.42:
        return hidden*smooth(t/.42)
    if t<.49:
        return hidden.copy()
    if t<.67:
        # Re-enter low, then rise nearly vertically through the idle holding lane.
        # Blade/grip orientation stays at idle throughout this 0.18-second cut.
        u=smooth((t-.49)/.18)
        control=Vector((.10,-.04,-.48))
        return hidden*(1-u)**2+control*(2*u*(1-u))+top*u*u
    if t<.73:
        return top.lerp(carry,smooth((t-.67)/.06))
    return carry*(1-smooth((t-.73)/(END-.73)))

receipts={}
for variant,entry in DATA['variants'].items():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    parents={b.name:(b.parent.name if b.parent else None) for b in rig.data.bones}
    local_rest={n:(rest[parents[n]].inverted()@m if parents[n] else m) for n,m in rest.items()}
    idle={n:canonical(row) for n,row in entry['world'].items()}
    reference={n:canonical(row) for n,row in DATA['reference'].items()}
    correction={n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    hidden=lower_right_offset(idle)
    rig.animation_data_create()
    action=bpy.data.actions.new('Sword_UppercutV4_'+variant)
    action.use_fake_user=True
    rig.animation_data.action=action
    frames=round(FPS*END)
    samples=[]
    previous={}
    blend_previous={}
    for i in range(frames+1):
        t=i/FPS
        shift=offset_at(t,hidden) if i not in (0,frames) else Vector((0,0,0))
        # Applying one translation to EVERY joint keeps all relative angles,
        # lengths, helper-bone support and both grip contact frames at idle.
        pose={n:pose_matrix(m.translation+shift,m.to_quaternion()) for n,m in idle.items()}
        ue={n:Matrix.LocRotScale(C@m.translation*100,
            (C@m.to_quaternion().to_matrix()@C).to_quaternion(),Vector(entry['world'][n]['s'])) for n,m in pose.items()}
        keys={}
        for n in NAMES:
            parent=DATA['parents'][n]
            local=ue[parent].inverted()@ue[n] if parent in ue else ue[n]
            p,q,s=local.decompose()
            if n in previous and q.dot(previous[n])<0:q=-q
            previous[n]=q.copy()
            keys[n]=dict(p=list(p),q=list(q),s=list(s))
        samples.append(dict(seconds=t,bones=keys))
        scene.frame_set(i)
        worlds={n:pose_matrix(pose[n].translation,pose[n].to_quaternion()@correction[n]) for n in rest}
        for bone in rig.pose.bones:
            parent_world=worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis=local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.rotation_mode='QUATERNION'
            q=bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q=-q
            bone.rotation_quaternion=q
            blend_previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(channel,frame=i,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=FPS
    scene.render.fps_base=1
    scene.frame_start=0
    scene.frame_end=frames
    scene.frame_set(0)
    out=P/variant
    out.mkdir(exist_ok=True)
    patch=dict(revision='LowerRightIdleGripUppercutV4',variant=variant,source_idle=entry['idle'],
               fps=FPS,intervals=frames,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend=out/'Sword_UppercutV4_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    receipts[variant]=dict(blend=str(blend),keys=str(out/'editable_keys.json'),seconds=END,
        hidden_offset_m=list(hidden),joint_processing='Rigid transport of current full idle pose')
    print('LOWER_RIGHT_UPPERCUT_V4_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='LowerRightIdleGripUppercutV4',
    sources='User-directed path and current installed idle poses; no external motion',
    paid_motion_used=False,phases=dict(lower_right=[0,.42],offscreen=[.42,.49],upward_cut=[.49,.67],
        carry=[.67,.73],recover=[.73,END]),fps=FPS,variants=receipts,
    runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
