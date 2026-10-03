"""A762 side charging: native grouped donor hand, whole-arm support and release."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;S=O.parent
sources=json.loads((O/'sources.json').read_text())['animations']
refs=json.loads((O/'reference_poses.json').read_text());donor=refs['ASH12']['samples']['140.4']
draft='--draft' in sys.argv
bpy.context.preferences.filepaths.save_version=0
H0=Matrix(donor['bones']['hand_r'])
# The A762 tab is the separate protrusion at the front of its bolt slot.
# Reuse the donor's grouped hook, placing the inner index pad beside the tab.
pad=Vector((-.0358,-.1694,.075))
H0.translation+=pad-Matrix(donor['bones']['index_03_r']).translation
turn=Quaternion(Vector((0,1,0)),math.radians(115)).to_matrix().to_4x4()
H0=Matrix.Translation(pad)@turn@Matrix.Translation(-pad)@H0
if (O/'fitted_contact.json').exists():
    fitted=json.loads((O/'fitted_contact.json').read_text())
    if not fitted['success']:raise RuntimeError('Contact adaptation is not ready')
    H0=Matrix(fitted['hand_in_root'])
fingers=[n for n in donor['basis'] if n.startswith(('thumb','index','middle','ring','pinky')) and n.endswith('_r')]
arm=['clavicle_r','upperarm_r','lowerarm_r','hand_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_twist_01_r','lowerarm_twist_02_r']
names=arm+fingers
def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(10.+t*(-15.+6.*t))
def mix(a,b,t):
    ap,aq,az=a.decompose();bp,bq,bz=b.decompose();return Matrix.LocRotScale(ap.lerp(bp,t),aq.slerp(bq,t),az)
def moved(H,p):
    H=H.copy();H.translation+=Vector(p);return H
def aimed(M,oldtip,origin,tip):
    return Matrix.LocRotScale(origin,(oldtip-M.translation).rotation_difference(tip-origin)@M.to_quaternion(),M.to_scale())
def curves(a):return {fc.data_path+'#'+str(fc.array_index):fc for la in a.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
def solve_arm(p,H,rest,w):
    old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_r','lowerarm_r','hand_r'
    C=old['clavicle_r'].translation.copy();A=old[un].translation.copy();E0=old[fn].translation.copy();T=H.translation
    l1=(E0-A).length;l2=(old[hn].translation-E0).length
    if (T-A).length>l1+l2-.004:
        R=(A-C).length;dist=(T-C).length;axis=(T-C).normalized()
        cosine=max(-1.,min(1.,(R*R+dist*dist-(l1+l2-.004)**2)/(2.*R*dist)))
        side=A-C-axis*(A-C).dot(axis);side.normalize()
        A=C+axis*(R*cosine)+side*(R*math.sqrt(max(0.,1.-cosine*cosine)))
        p['clavicle_r']=aimed(old['clavicle_r'],old[un].translation,C,A)
    axis=(T-A).normalized();dist=(T-A).length
    oldpole=E0-A-axis*(E0-A).dot(axis);oldpole.normalize()
    delta=H.to_quaternion()@rest[hn].to_quaternion().inverted()
    rest_axis=(rest[hn].translation-rest[fn].translation).normalized()
    ideal=T-(delta@rest_axis)*l2-A;ideal-=axis*ideal.dot(axis)
    pole=oldpole
    if ideal.length>.00001:
        ideal.normalize();angle=math.atan2(axis.dot(oldpole.cross(ideal)),oldpole.dot(ideal))
        pole=Quaternion(axis,angle*w)@oldpole
    along=(l1*l1-l2*l2+dist*dist)/(2.*dist)
    E=A+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
    p[un]=aimed(old[un],E0,A,E)
    carried=aimed(old[fn],old[hn].translation,E,T)
    coherent=(delta@rest_axis).rotation_difference((T-E).normalized())@delta@rest[fn].to_quaternion()
    p[fn]=Matrix.LocRotScale(E,carried.to_quaternion().slerp(coherent,w),old[fn].to_scale())
    for parent in (un,fn):
        for n in [parent.replace('_r','_twist_01_r'),parent.replace('_r','_twist_02_r')]:
            p[n]=mix(p[parent]@old[parent].inverted()@old[n],p[parent]@rest[parent].inverted()@rest[n],w)
    p[hn]=H
receipt={};report={}
for info in sources[:1] if draft else sources:
    source=Path(info['source'][0]).with_suffix('.blend')
    bpy.ops.wm.open_mainfile(filepath=str(O/'Working.blend') if info['family']=='base' else str(source))
    r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;old=r.animation_data.action
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
    local={n:rest[parents[n]].inverted()@rest[n] for n in names}
    def read(f):
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
    begin=read(270);end=read(402);contact=read(310);pulled=read(344)
    root0=contact['WPN_root'].inverted();bolt0=(root0@contact['WPN_bolt']).translation
    B0=begin['WPN_root'].inverted()@begin['hand_r'];B1=end['WPN_root'].inverted()@end['hand_r']
    pull=(pulled['WPN_root'].inverted()@pulled['WPN_bolt']).translation-bolt0
    release=moved(H0,pull)
    midway=mix(release,B1,.65);midway.translation=Vector((-.085,.115,.075))
    keys=[(270,B0),(296,moved(H0,(-.025,.035,.012))),(310,H0),(344,release),
          (354,moved(release,(-.042,.018,.018))),(372,midway),(402,B1)]
    def hand_at(f,p):
        if 310<=f<=344:
            return moved(H0,(p['WPN_root'].inverted()@p['WPN_bolt']).translation-bolt0)
        for (t0,a),(t1,b) in zip(keys,keys[1:]):
            if f<=t1:return mix(a,b,smooth((f-t0)/(t1-t0)))
        return B1
    original=curves(old);frames=[float(k.co.x) for k in original['pose.bones["hand_r"].rotation_quaternion#0'].keyframe_points]
    samples={}
    for f in frames:
        if not 270<f<402:continue
        p=read(f);q0={n:r.pose.bones[n].rotation_quaternion.copy() for n in names}
        w=smooth((f-270)/24)*(1.-smooth((f-374)/28))
        H=p['WPN_root']@hand_at(f,p);solve_arm(p,H,rest,w)
        finger_weight=smooth((f-270)/34)*(1.-smooth((f-346)/56))
        samples[f]={n:(q0[n].slerp(Quaternion(donor['basis'][n]),finger_weight) if n in fingers else
            (local[n].inverted()@p[parents[n]].inverted()@p[n]).to_quaternion()) for n in names}
    action=old.copy();action.name=source.stem+'_RightChargeNatural';action.use_fake_user=True
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];new=curves(action)
    for n in names:
        tracks=[new[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)];prev=None
        for i,k in enumerate(tracks[0].keyframe_points):
            f=float(k.co.x);q=samples[f][n].copy() if f in samples else Quaternion([c.keyframe_points[i].co.y for c in tracks])
            if prev is not None and prev.dot(q)<0:q.negate()
            prev=q.copy()
            for j,c in enumerate(tracks):c.keyframe_points[i].co.y=q[j];c.keyframe_points[i].interpolation='LINEAR'
        for c in tracks:c.update()
    metrics={}
    for f in [270,280,296,310,320,340,344,350,354,365,380,395,402]:
        p=read(f);a=(p['hand_r'].translation-p['lowerarm_r'].translation).normalized()
        b=(p['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted())@(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
        metrics[f]={'wrist_bend':math.degrees(a.angle(b))}
    allowed={f'pose.bones["{n}"].rotation_quaternion#{i}' for n in names for i in range(4)}
    outside=[key for key,c in original.items() if key not in allowed and
        (len(c.keyframe_points)!=len(new[key].keyframe_points) or any(a.co!=b.co for a,b in zip(c.keyframe_points,new[key].keyframe_points)))]
    report[info['family']]={'samples':metrics,'changed_tracks_outside_right_rotations':outside}
    (O/'authored_pose_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('RIGHT_CHARGE_AUTHOR',info['family'],metrics,flush=True)
    s.frame_set(320);bpy.context.view_layer.update()
    if draft:
        bpy.ops.wm.save_as_mainfile(filepath=str(O/'Draft.blend'));break
    dest=O/info['family'];dest.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(source.stem+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(dest/(source.stem+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    receipt[info['family']]={**info,'original_blend':str(source),'blend':str(dest/(source.stem+'.blend')),'fbx':str(dest/(source.stem+'.fbx')),
        'fps':120,'rate':120,'frames':[0,515],'changed_bones':names,'edit_frames':[270,402],'contact_frames':[310,344],
        'weights_changed':False,'game_tested':False}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
