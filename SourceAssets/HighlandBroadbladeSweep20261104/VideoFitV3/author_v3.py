"""Bake tracked screen-space sword, wrist and elbow targets on the native FPS rig."""
from pathlib import Path
import importlib.util
import json
import math
import bpy
from mathutils import Matrix, Quaternion, Vector

HERE=Path(__file__).resolve().parent
TAKE=HERE.parent
spec=importlib.util.spec_from_file_location('support',TAKE.parent/'SwordUppercut20261003/GripRecoveryV15/arm_support.py')
A=importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
POSES=json.loads((TAKE/'grip_poses.json').read_text())
FPS=120

def blend(a,b,t):
    p,q,s=a.decompose(); v,r,z=b.decompose()
    return A.mat(p.lerp(v,t),q.slerp(r,t),s.lerp(z,t))

def transform(row,scale):
    x,y,z,w=row['q'];return A.mat(Vector(row['p'])*.01,Quaternion((w,x,y,z)),scale)

def grasp_angle(weapon,hand):
    p=(weapon.inverted()@hand).translation; return math.atan2(p.y,p.x)

def blade_angles(matrix):
    forward=matrix.to_quaternion()@Vector((0,0,1)); across=matrix.to_quaternion()@Vector((1,0,0))
    yaw=math.atan2(forward.x,forward.y);pitch=math.asin(max(-1.,min(1.,forward.z)))
    flat=Vector((-math.cos(yaw),math.sin(yaw),0))
    return yaw,pitch,math.atan2(across.dot(forward.cross(flat)),across.dot(flat))

def heavy_handoff(start,end,amount,anchor):
    if amount>=1.:return end
    y0,p0,r0=blade_angles(start);y1,p1,r1=blade_angles(anchor)
    # Lift the heavy landing blade through the forward hemisphere. The shorter
    # quaternion arc turns it backwards through the camera, across the face.
    yaw=y0+(y1-y0)*amount; pitch=min(math.radians(84),p0+(p1-p0)*amount+math.radians(16)*math.sin(math.pi*amount))
    roll=r0+(A.near_angle(r1,r0)-r0)*amount
    forward=Vector((math.sin(yaw)*math.cos(pitch),math.cos(yaw)*math.cos(pitch),math.sin(pitch)))
    across=Quaternion(forward,roll)@Vector((-math.cos(yaw),math.sin(yaw),0))
    rotation=Matrix((across,forward.cross(across),forward)).transposed().to_quaternion()
    # The tracked blade passes vertical during anticipation. Decomposing each
    # live frame there introduces a 180-degree yaw/roll coordinate switch.
    # Resolve the handoff at one endpoint, then apply the small tracked delta.
    correction=end.to_quaternion()@anchor.to_quaternion().inverted()
    rotation=Quaternion().slerp(correction,amount**3)@rotation
    return A.mat(start.translation.lerp(end.translation,amount),rotation,end.to_scale())

def place_arm(pose,idle,entry,supported,side,elbow_hint,enter,recover,handoff):
    c,u,l,h=[key+'_'+side for key in ('clavicle','upperarm','lowerarm','hand')]
    a0,e0,h0=[idle[k].translation for k in (u,l,h)]; upper0=e0-a0;lower0=h0-e0
    upper_len=upper0.length;lower_len=lower0.length
    # Reconstruct the shoulder from the reference elbow and anatomical humerus.
    # The reference elbow stays on its recorded screen ray even when crossing.
    target=pose[h].translation
    carry=pose[h].to_quaternion()@supported[h].to_quaternion().inverted()
    entry_direction=carry@(supported[l].translation-supported[h].translation).normalized()
    target_direction=(elbow_hint-target).normalized()
    swing=entry_direction.rotation_difference(target_direction)
    guide_direction=Quaternion().slerp(swing,enter)@entry_direction
    return_direction=(e0-h0).normalized()
    guide_direction=Quaternion().slerp(guide_direction.rotation_difference(return_direction),recover)@guide_direction
    if handoff:
        direction,weight=handoff
        guide_direction=Quaternion().slerp(guide_direction.rotation_difference(direction),weight)@guide_direction
    elbow=target+lower_len*guide_direction
    shoulder_hint=entry[u].translation.lerp(a0,enter)
    shoulder=elbow+upper_len*(shoulder_hint-elbow).normalized()
    upper=elbow-shoulder;lower=target-elbow
    du=A.frame(upper,upper.cross(lower))@A.frame(upper0,upper0.cross(lower0)).inverted()
    dl=(du@lower0.normalized()).rotation_difference(lower.normalized())@du
    hand_rotation=pose[h].to_quaternion()@idle[h].to_quaternion().inverted()
    aligned=(hand_rotation@lower0.normalized()).rotation_difference(lower.normalized())@hand_rotation
    principal=A.axis_angle(aligned@dl.inverted(),lower.normalized())
    # A full turn is identity at the wrist but becomes a destructive half turn
    # on a 50% helper. Bind all three stations to the same anatomical branch.
    twist=.7*math.sin(principal)
    dl=Quaternion(lower.normalized(),-twist)@aligned
    pose[c]=idle[c].copy();pose[c].translation+=shoulder-a0
    pose[u]=A.mat(shoulder,du@idle[u].to_quaternion(),idle[u].to_scale())
    pose[l]=A.mat(elbow,dl@idle[l].to_quaternion(),idle[l].to_scale())
    for bone,direction,old_direction in [(u,upper,entry[l].translation-entry[u].translation),(l,lower,entry[h].translation-entry[l].translation)]:
        carried=old_direction.rotation_difference(direction)@entry[bone].to_quaternion()
        pose[bone]=A.mat(pose[bone].translation,carried.slerp(pose[bone].to_quaternion(),enter),pose[bone].to_scale())
    for stem,origin,old_origin,delta,parent in [('upperarm',shoulder,a0,du,u),('lowerarm',elbow,e0,dl,l)]:
        for suffix,share in [('01',1.),('02',.5)]:
            n=f'{stem}_twist_{suffix}_{side}'; q=delta@idle[n].to_quaternion()
            if stem=='lowerarm':q=Quaternion(lower.normalized(),twist*share)@q
            solved=A.mat(origin+delta@(idle[n].translation-old_origin),q,idle[n].to_scale())
            pose[n]=blend(pose[parent]@entry[parent].inverted()@entry[n],solved,enter)
    # Blend the two constant bind offsets in palm space, then point the whole
    # set of stations along the forearm. Independent world-space slerps used
    # different quaternion branches halfway out of the heavy landing pose.
    for n,base_share in [(l,1.),('lowerarm_twist_02_'+side,.5),('lowerarm_twist_01_'+side,0.)]:
        start=supported[h].to_quaternion().inverted()@supported[n].to_quaternion()
        end=idle[h].to_quaternion().inverted()@idle[n].to_quaternion()
        q=pose[h].to_quaternion()@start.slerp(end,enter)
        basis=idle[n].to_quaternion().inverted()@lower0.normalized()
        q=(q@basis).rotation_difference(lower.normalized())@q
        q=Quaternion(lower.normalized(),-twist*base_share*enter)@q
        pose[n]=A.mat(pose[n].translation,q,pose[n].to_scale())

def ue_keys(pose,previous):
    world={n:A.mat(A.C@m.translation*100,(A.C@m.to_quaternion().to_matrix()@A.C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
    out={}
    for n,m in A.localize(world).items():
        p,q,s=m.decompose()
        if n in previous and previous[n].dot(q)<0:q.negate()
        previous[n]=q.copy();out[n]={'p':list(p),'q':list(q),'s':list(s)}
    return out

def bake(variant):
    grip=variant.split('_')[0]; data=POSES[grip]; idle=A.pose_from_rows(data['idle']); ready=variant.endswith('_FromReady');entry=idle if ready else A.pose_from_rows(data['land']); rows=json.loads((HERE/(grip+'-fit.json')).read_text());last=2*(len(rows)-1)
    bpy.ops.wm.open_mainfile(filepath=str(A.SOURCE));bpy.context.preferences.filepaths.save_version=0
    rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE');rig.animation_data_clear();rig.animation_data_create();act=bpy.data.actions.new('Highland_Sweep_VideoFit_'+variant);rig.animation_data.action=act
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones};local_rest=A.localize(rest);ref={n:A.canonical(A.native(k)) for n,k in A.DATA['reference'].items()};correction={n:ref[n].inverted()@rest[n] for n in rest}
    previous={};basis_previous={};output=[]; grip_z=Vector((0.,0.,1.))
    anchor=blend(transform(rows[11],(1,1,1)),transform(rows[12],(1,1,1)),.4)
    handoffs=None if ready else json.loads((HERE/'heavy-handoff.json').read_text())[grip]
    supported=idle.copy() if ready else entry.copy()
    if not ready:
        surface=json.loads((TAKE/'Review/ReferenceV2'/grip/'surface.json').read_text(encoding='utf-8-sig'))['frames'][0]['bones']
        for n,row in surface.items():
            x,y,z,w=row['q'];supported[n]=A.canonical(A.mat(row['p'],Quaternion((w,x,y,z)),row['s']))
        for side in ('r','l'):
            h='hand_'+side;spin=grasp_angle(entry['WPN_root'],entry[h])-grasp_angle(idle['WPN_root'],idle[h]);raw=entry['WPN_root']@Quaternion(grip_z,spin).to_matrix().to_4x4()@idle['WPN_root'].inverted()@idle[h]
            supported[h]=A.mat(supported[h].translation,raw.to_quaternion(),raw.to_scale())
    for i in range(last+1):
        t=i/FPS; j=i//2; alpha=(i%2)/2; a,b=rows[j],rows[min(j+1,len(rows)-1)]
        enter=A.smooth(t/(.095 if ready else .19));recover=A.smooth((i-(last-13))/13)
        pose={n:blend(entry[n],idle[n],enter) for n in A.NAMES};scale=idle['WPN_root'].to_scale()
        weapon=blend(transform(a,scale),transform(b,scale),alpha)
        weapon=blend(entry['WPN_root'],weapon,enter) if ready else heavy_handoff(entry['WPN_root'],weapon,enter,anchor)
        weapon=blend(weapon,idle['WPN_root'],recover)
        move=weapon@idle['WPN_root'].inverted()
        for n in A.descendants('WPN_root')|{'ik_hand_gun'}:pose[n]=move@idle[n]
        # Keep the WPN parent and its child on a shared handoff. A jump in their
        # relative transform is magnified by the runtime parent-space entry blend.
        pose['ik_hand_gun']=weapon@blend(entry['WPN_root'].inverted()@entry['ik_hand_gun'],idle['WPN_root'].inverted()@idle['ik_hand_gun'],enter)
        for s,side in enumerate(('r','l')):
            h='hand_'+side;spin=a['spin'][s]*(1-alpha)+b['spin'][s]*alpha
            init=grasp_angle(entry['WPN_root'],entry[h])-grasp_angle(idle['WPN_root'],idle[h]);init=A.near_angle(init,rows[min(7 if ready else 11,len(rows)-1)]['spin'][s]);spin=(init*(1-enter)+spin*enter)*(1-recover)
            hand=weapon@Quaternion(grip_z,spin).to_matrix().to_4x4()@idle['WPN_root'].inverted()@idle[h]
            for n in A.HANDS[side]:pose[n]=hand@idle[h].inverted()@idle[n]
            hint=Vector(a['elbows'][s]).lerp(Vector(b['elbows'][s]),alpha)*.01
            handoff=(Vector(handoffs[side][i]),1.-A.smooth((i-22)/6)) if handoffs and i<28 else None
            place_arm(pose,idle,entry,supported,side,hint,enter,recover,handoff);ik='ik_hand_'+side;pose[ik]=hand@idle[h].inverted()@idle[ik]
        if i==0:pose=entry
        if i==last:pose=idle
        output.append(ue_keys(pose,previous)); world={n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent=world[bone.parent.name] if bone.parent else Matrix.Identity(4);bone.rotation_mode='QUATERNION';bone.matrix_basis=local_rest[bone.name].inverted()@parent.inverted()@world[bone.name];q=bone.rotation_quaternion.copy()
            if bone.name in basis_previous and basis_previous[bone.name].dot(q)<0:q.negate()
            basis_previous[bone.name]=q.copy();bone.rotation_quaternion=q
            for ch in ('location','rotation_quaternion','scale'):bone.keyframe_insert(ch,frame=i,group=bone.name)
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    bpy.context.scene.frame_start=0;bpy.context.scene.frame_end=last;bpy.context.scene.render.fps=FPS;bpy.context.scene.frame_set(0)
    (TAKE/(variant+'.json')).write_text(json.dumps(dict(skeleton=data['skeleton'],fps=FPS,frames=output),separators=(',',':')))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/('Highland_Sweep_VideoFit_'+variant+'.blend')))
    print('BAKED',variant,len(output),flush=True)

if __name__ == '__main__':
    for variant in ('Standard','LongGrip','Standard_FromReady','LongGrip_FromReady'):bake(variant)
