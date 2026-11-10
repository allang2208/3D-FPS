"""Bake Lian Zhan on the accepted bare-arm native rig, preserving both grasps."""
from pathlib import Path
import json
import runpy
from math import radians, tanh
import bpy
from mathutils import Matrix, Quaternion, Vector

P=Path(__file__).resolve().parent
helpers=runpy.run_path(str(P.parent/'HighlandBroadbladeSweep20261104/VideoFitV3/author_v3.py'))
A=helpers['A'];transform=helpers['transform']
ue_keys=helpers['ue_keys']
FPS=120
DATA=json.loads((P/'grip_poses.json').read_text())

def smoothstep(t):
    t=max(0.,min(1.,t))
    return t*t*(3.-2.*t)

def widen_swing(row,time,duration):
    # Add width to the existing arc in camera space. Carry the grip, elbows
    # and shoulders together so the local wrist and elbow poses stay intact.
    weight=smoothstep(time/.18)*smoothstep((duration-time)/.65)
    hilt=Vector(row['p'])
    # Turn about the hilt, with a depth budget at the far shoulder. This
    # keeps the hilt on its original depth plane at wide screen crossings.
    depth_budget=4.0
    shoulder_lever=55.+abs(hilt.x)+.12*(abs(hilt.y)+35.)
    yaw_limit=depth_budget/shoulder_lever
    yaw=-weight*yaw_limit*tanh(radians(10.)*hilt.x/(32.*yaw_limit))
    turn=Quaternion((0.,0.,1.),yaw)
    turned_hilt=turn@hilt
    offset=Vector((hilt.x*(1.+.35*weight)-turned_hilt.x,hilt.y-turned_hilt.y,0.))
    x,y,z,w=row['q']
    q=turn@Quaternion((w,x,y,z))
    arms={side:{joint:turn@Vector(point)+offset for joint,point in joints.items()}
          for side,joints in row['arms'].items()}
    return dict(p=list(turned_hilt+offset),q=[q.x,q.y,q.z,q.w],arms=arms)

def support_arm(pose,idle,side,goals):
    n=lambda stem:stem+'_'+side
    s0,e0,w0=[idle[n(b)].translation for b in ('upperarm','lowerarm','hand')]
    w=pose[n('hand')].translation
    e=Vector(goals['elbow'])*.01
    s=Vector(goals['shoulder'])*.01
    carry=pose[n('hand')].to_quaternion()@idle[n('hand')].to_quaternion().inverted()
    f=(w-e).normalized()
    u=(e-s).normalized()
    fore=(carry@(w0-e0).normalized()).rotation_difference(f)@carry
    upper=(fore@(e0-s0).normalized()).rotation_difference(u)@fore
    for name in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_02','lowerarm_twist_01'):
        proximal=name.startswith(('clavicle','upperarm'))
        ref=idle[n(name)]
        turn=upper if proximal else fore
        origin,old=(s,s0) if proximal else (e,e0)
        pose[n(name)]=A.mat(origin+turn@(ref.translation-old),turn@ref.to_quaternion(),ref.to_scale())

def bake(grip):
    data=DATA[grip];idle=A.pose_from_rows(data['idle'])
    rows=json.loads((P/'RootClearance/arm-path.json').read_text())[grip];last=len(rows)-1
    bpy.ops.wm.open_mainfile(filepath=str(A.SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.animation_data_create()
    act=bpy.data.actions.new('ChainSlash_'+grip);rig.animation_data.action=act
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones};local_rest=A.localize(rest)
    ref={n:A.canonical(A.native(k)) for n,k in A.DATA['reference'].items()}
    correction={n:ref[n].inverted()@rest[n] for n in rest}
    previous={};basis_previous={};output=[]
    for i in range(last+1):
        a=widen_swing(rows[i],i/FPS,last/FPS)
        pose={n:m.copy() for n,m in idle.items()}
        weapon=transform(a,idle['WPN_root'].to_scale())
        change=weapon@idle['WPN_root'].inverted()
        for n in A.descendants('WPN_root')|{'ik_hand_gun'}:pose[n]=change@idle[n]
        for side in ('r','l'):
            # Each palm and every finger keep their exact accepted sword-space
            # matrix. No per-frame finger or wrist correction can loosen a grip.
            for n in A.HANDS[side]|{'ik_hand_'+side}:pose[n]=change@idle[n]
            support_arm(pose,idle,side,a['arms'][side])
        if i in (0,last):pose={n:m.copy() for n,m in idle.items()}
        output.append(ue_keys(pose,previous))
        world={n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent=world[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.rotation_mode='QUATERNION'
            bone.matrix_basis=local_rest[bone.name].inverted()@parent.inverted()@world[bone.name]
            q=bone.rotation_quaternion.copy()
            if bone.name in basis_previous and basis_previous[bone.name].dot(q)<0:q.negate()
            basis_previous[bone.name]=q.copy();bone.rotation_quaternion=q
            for ch in ('location','rotation_quaternion','scale'):bone.keyframe_insert(ch,frame=i,group=bone.name)
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=last;scene.render.fps=FPS;scene.frame_set(0)
    rig['SkillName']='连斩';rig['WeaponRequirement']='TwoHandedSword';rig['ReferenceStartSeconds']=37.3
    payload=dict(skeleton=data['skeleton'],fps=FPS,frames=output,reference_start=37.3,reference_end=40.,
        markers=[['Cut1',.30],['Cut2',.85],['Cut3',1.35],['Cut4',1.70],['Recover',2.22]],
        stage='playable_skill_test',weapon_requirement='two_handed_sword')
    (P/(grip+'.json')).write_text(json.dumps(payload,separators=(',',':')))
    bpy.ops.wm.save_as_mainfile(filepath=str(P/('ChainSlash_'+grip+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(P/('ChainSlash_'+grip+'.fbx')),use_selection=True,
        object_types={'ARMATURE'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.,axis_forward='-Y',axis_up='Z')
    print('CHAIN_SLASH_BAKED',grip,len(output),'keys',last/FPS,'seconds',flush=True)

if __name__=='__main__':
    for grip in ('Standard','LongGrip'):bake(grip)
