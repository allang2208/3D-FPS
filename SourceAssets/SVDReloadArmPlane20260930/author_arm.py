"""SVD-only reload arm authoring, using the currently published contact tracks.

Keep the wrist/fingers and weapon in component space. Solve the elbow with fixed
segment lengths, align the upper arm's anatomical hinge, and derive forearm roll
from palm width rather than transporting an unrelated shortest-arc quaternion.
The existing shoulder camera relocation remains the input. Helpers follow the
complete segment transform; no skin/bind changes and no runtime correction layer.
"""
import bpy, json, math, sys, hashlib
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P = Path('D:/FPS3D/FPSGAME')
O = Path(__file__).parent
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
EXPORT = '--export' in ARGS
FAMILIES = [a for a in ARGS if a in ('base','angled','canted','prism','vertical')] or ['base','angled','canted','prism','vertical']
NAMES = ['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']


def ease(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10.+x*(-15.+6.*x))


def weight(f, end):
    return ease(f/36.) * ease((end-f)/48.)


def frame(axis, transverse, normal=False):
    x = axis.normalized()
    t = (transverse-x*transverse.dot(x)).normalized()
    if normal:
        z=t; y=z.cross(x).normalized()
    else:
        y=t; z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()


def signed(a,b,axis):
    a=(a-axis*a.dot(axis)).normalized();b=(b-axis*b.dot(axis)).normalized()
    return math.atan2(axis.dot(a.cross(b)),a.dot(b))


def sample(rig, action, count):
    rig.animation_data.action=action
    rig.animation_data.action_slot=action.slots[0]
    result=[]
    for f in range(count+1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        result.append({b.name:b.matrix.copy() for b in rig.pose.bones})
    return result


def solve(old, rest, w, previous_angle=0.):
    if w<=1.e-8:
        return {n:m.copy() for n,m in old.items()},dict(pole_angle=0.)
    un,ln,hn='upperarm_l','lowerarm_l','hand_l'
    A,E,H=(old[n].translation.copy() for n in (un,ln,hn))
    RA,RE,RH=(rest[n].translation for n in (un,ln,hn))
    ru,rl=RE-RA,RH-RE
    rp=ru.cross(rl).normalized()
    l1,l2=(E-A).length,(H-E).length
    # Keep a modest bend while the support hand is moving. Fade at clip boundaries
    # to the exact currently accepted idle/grip pose, with no hand-position change.
    supported=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(30)))
    reach=H-A
    if reach.length>supported:
        A=A.lerp(H-reach.normalized()*supported,w)
    axis=(H-A).normalized();dist=(H-A).length
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    height=math.sqrt(max(0.,l1*l1-along*along))
    # Parallel-transport the original bend plane to the adjusted reach axis.
    old_axis=(H-old[un].translation).normalized()
    turn=old_axis.rotation_difference(axis)
    pole=turn @ ((E-old[un].translation)-old_axis*(E-old[un].translation).dot(old_axis)).normalized()
    across=rest['index_01_l'].translation-rest['pinky_01_l'].translation
    hd=old[hn].to_quaternion() @ rest[hn].to_quaternion().inverted()
    palm=hd @ across
    hand_axis=hd @ rl.normalized()

    def candidate(deg):
        e=A+axis*along+(Quaternion(axis,math.radians(deg))@pole)*height
        ud,ld=(e-A).normalized(),(H-e).normalized()
        pl=ud.cross(ld).normalized()
        ql=frame(ld,palm) @ frame(rl,across).inverted() @ rest[ln].to_quaternion()
        lower_plane=(ql @ rest[ln].to_quaternion().inverted())@rp
        roll=signed(lower_plane,pl,ld)
        bend=math.degrees(ld.angle(hand_axis))
        # Move the elbow only when that reduces an excessive pronation or wrist
        # axis bend; prefer the author's existing path and temporal continuity.
        penalty=(max(0.,abs(math.degrees(roll))-70.)/25.)**2
        penalty+=(max(0.,bend-40.)/30.)**2
        penalty+=(deg/65.)**2 + ((deg-previous_angle)/18.)**2
        return penalty,e,ud,ld,pl,ql,roll,bend

    angles=range(-100,101,4)
    chosen=min(angles,key=lambda a:candidate(a)[0])
    # Refine the coarse search continuously: discrete pole steps would create
    # tiny elbow snaps even though the per-frame solver itself is continuous.
    left,right=max(-100.,chosen-4.),min(100.,chosen+4.)
    for _ in range(16):
        x=left+(right-left)/3.;y=right-(right-left)/3.
        if candidate(x)[0]<candidate(y)[0]:right=y
        else:left=x
    chosen=(left+right)*.5
    # Fractional weight controls both pole movement and joint orientation. The
    # resulting quaternion interpolation is axial because both frames aim at the
    # same solved bone direction; it cannot shorten the segment.
    _,NE,ud,ld,pl,ql,roll,bend=candidate(chosen*w)
    qu=frame(ud,pl,True) @ frame(ru,rp,True).inverted() @ rest[un].to_quaternion()
    # Share a bounded amount of the palm roll through the upper segment to avoid
    # concentrating the whole rotation at the elbow skin seam.
    support=max(-math.radians(12.),min(math.radians(12.),-roll*.18))
    qu=Quaternion(ud,support)@qu
    out={n:m.copy() for n,m in old.items()}
    for name,pos,tip,q in ((un,A,NE,qu),(ln,NE,H,ql)):
        old_tip=old[ln].translation if name==un else H
        swing=(old_tip-old[name].translation).rotation_difference(tip-pos)
        aligned=swing@old[name].to_quaternion()
        out[name]=Matrix.LocRotScale(pos,aligned.slerp(q,w),old[name].to_scale())
        delta=out[name]@old[name].inverted()
        for suffix in ('01','02'):
            helper=name.replace('_l','_twist_'+suffix+'_l')
            if helper in out:out[helper]=delta@old[helper]
    # Carry the shoulder girdle without the old overwritten-clavicle assignment.
    out['clavicle_l']=old['clavicle_l'].copy()
    out['clavicle_l'].translation+=A-old[un].translation
    return out,dict(pole_angle=chosen*w,forearm_roll=math.degrees(roll),wrist_axis_bend=bend)


def metrics(pose,rest):
    a,e,h=(pose[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
    ra,re,rh=(rest[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
    ud,ld=(e-a).normalized(),(h-e).normalized();rp=(re-ra).cross(rh-re).normalized()
    pl=ud.cross(ld).normalized()
    up=(pose['upperarm_l'].to_quaternion()@rest['upperarm_l'].to_quaternion().inverted())@rp
    lo=(pose['lowerarm_l'].to_quaternion()@rest['lowerarm_l'].to_quaternion().inverted())@rp
    return dict(upper_roll=math.degrees(signed(up,pl,ud)),lower_roll=math.degrees(signed(lo,pl,ld)),flex=math.degrees(ud.angle(ld)))


def curves(action):
    return {(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}


def bake(rig,source,rest,poses,end,name):
    action=source.copy();source.name='BEFORE_ARM_PLANE_'+name;source.use_fake_user=True
    action.name=name;action.use_fake_user=True
    tracks=curves(action)
    for n in NAMES:
        parent=rig.data.bones[n].parent.name
        lr=rest[parent].inverted()@rest[n]
        values=[(lr.inverted()@p[parent].inverted()@p[n]).decompose() for p in poses]
        for prop,k,count in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            previous=None;rows=[]
            for v in values:
                v=v[k].copy()
                if prop=='rotation_quaternion':
                    if previous and previous.dot(v)<0:v.negate()
                    previous=v.copy()
                rows.append(v)
            for j in range(count):
                c=tracks[(f'pose.bones["{n}"].{prop}',j)]
                c.keyframe_points.clear();c.keyframe_points.add(end+1)
                c.keyframe_points.foreach_set('co',[x for f,row in enumerate(rows) for x in (f,row[j])])
                for point in c.keyframe_points:point.interpolation='LINEAR'
                c.update()
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    return action


def main():
    for family in FAMILIES:
        for clip,end in (('reload',400),('reload_empty',515)):
            src=P/'SourceAssets/SVDReloadLeftArm20260925/Blends'/f'SVD_{family}_{clip}_LeftArm.blend'
            bpy.ops.wm.open_mainfile(filepath=str(src),use_scripts=False)
            rig=bpy.data.objects['SK_M4_Infima']
            for ob in bpy.context.scene.objects:
                if ob.type=='MESH':ob.hide_viewport=True
            name='A_SVD_'+('' if family=='base' else family+'_')+clip
            source=bpy.data.actions[name]
            rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
            old=sample(rig,source,end);new=[];rows=[];previous=0.
            for f,p in enumerate(old):
                fixed,details=solve(p,rest,weight(f,end),previous)
                previous=details['pole_angle'];new.append(fixed)
                rows.append(dict(frame=f,weight=weight(f,end),before=metrics(p,rest),after=metrics(fixed,rest),**details))
            full=[r for r in rows if 240<=r['frame']<=344]
            immutable=[n for n in rest if n not in NAMES or n=='hand_l']
            invariant_error=max(max(abs(old[f][n][i][j]-new[f][n][i][j]) for i in range(4) for j in range(4)) for f in range(end+1) for n in immutable)
            length_error=max(abs((new[f][a].translation-new[f][b].translation).length-(old[f][a].translation-old[f][b].translation).length) for f in range(end+1) for a,b in [('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')])
            report=dict(family=family,clip=clip,frames=end,action=name,source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                summary=dict(before_max_upper_roll=max(abs(r['before']['upper_roll']) for r in full),after_max_upper_roll=max(abs(r['after']['upper_roll']) for r in full),
                    before_min_flex=min(r['before']['flex'] for r in full),after_min_flex=min(r['after']['flex'] for r in full),max_pole_adjustment=max(abs(r['pole_angle']) for r in rows),hand_fingers_weapon_matrix_error=invariant_error,bone_length_error_m=length_error),rows=rows,game_tested=False)
            if EXPORT:
                bake(rig,source,rest,new,end,name)
                scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
                scene.frame_start=0;scene.frame_end=end;scene.frame_set(304);bpy.context.view_layer.update()
                (O/'Blends').mkdir(exist_ok=True);(O/'Animations').mkdir(exist_ok=True)
                dest=O/'Blends'/f'SVD_{family}_{clip}_ArmPlane.blend'
                bpy.ops.wm.save_as_mainfile(filepath=str(dest))
                for ob in scene.objects:ob.select_set(ob==rig)
                bpy.context.view_layer.objects.active=rig
                fbx=O/'Animations'/f'{name}.fbx'
                bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
                report.update(blend=str(dest),fbx=str(fbx))
                # Native rest and author matrices allow the same-chain skinning
                # diagnosis to include the active chainmail's three saved LODs.
                (O/f'poses_{family}_{clip}.json').write_text(json.dumps(dict(rest={n:list(map(list,m)) for n,m in rest.items()},samples=[dict(frame=f,before={n:list(map(list,m)) for n,m in old[f].items()},after={n:list(map(list,m)) for n,m in new[f].items()}) for f in range(0,end+1,4)])))
            (O/f'authoring_{family}_{clip}.json').write_text(json.dumps(report,indent=2))
            print('ARM_PLANE',family,clip,report['summary'],flush=True)


if __name__=='__main__':main()
