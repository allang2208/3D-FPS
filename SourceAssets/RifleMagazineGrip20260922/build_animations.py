"""Re-author only magazine-holding left-arm tracks on the installed action families."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
sources=json.loads((O/'sources.json').read_text())['animations']
fits=json.loads((O/'selected_grasp.json').read_text())
bpy.context.preferences.filepaths.save_version=0
selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
receipt=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def mix(a,b,t):
    al,aq,az=a.decompose();bl,bq,bz=b.decompose()
    return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),az)
def aimed(old,oldtail,origin,target):
    q=(oldtail-old.translation).rotation_difference(target-origin)@old.to_quaternion()
    return Matrix.LocRotScale(origin,q,old.to_scale())
def solve_arm(p,H,rest,weight):
    old={n:m.copy() for n,m in p.items()}
    un,fn,hn='upperarm_l','lowerarm_l','hand_l'
    A=old[un].translation.copy();E0=old[fn].translation;T=H.translation
    l1=(E0-A).length;l2=(old[hn].translation-E0).length
    if (T-A).length>l1+l2-.003:
        C=old['clavicle_l'].translation;R=(A-C).length;distance=(T-C).length;axis=(T-C).normalized()
        cosine=max(-1,min(1,(R*R+distance*distance-(l1+l2-.003)**2)/(2*R*distance)))
        side=A-C-axis*(A-C).dot(axis);side.normalize()
        A=C+axis*(R*cosine)+side*(R*math.sqrt(max(0,1-cosine*cosine)))
        p['clavicle_l']=aimed(old['clavicle_l'],old[un].translation,C,A)
    axis=(T-A).normalized();dist=(T-A).length
    pole=E0-A-axis*(E0-A).dot(axis)
    hand_delta=H.to_quaternion()@rest[hn].to_quaternion().inverted()
    rest_forearm=(rest[hn].translation-rest[fn].translation).normalized()
    ideal=T-(hand_delta@rest_forearm)*l2-A;ideal-=axis*ideal.dot(axis)
    if ideal.length>.0001 and pole.dot(ideal)>0:
        pole=pole.normalized().lerp(ideal.normalized(),.40*weight)
    pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p[un]=aimed(old[un],E0,A,E)
    p[fn]=aimed(old[fn],old[hn].translation,E,T)
    # Rotate complete forearm and helper bones together; do not collapse the
    # glove/sleeve with half-strength twist on a separately rotating segment.
    target_q=(hand_delta@rest_forearm).rotation_difference((T-E).normalized())@hand_delta@rest[fn].to_quaternion()
    p[fn]=Matrix.LocRotScale(E,p[fn].to_quaternion().slerp(target_q,.55*weight),old[fn].to_scale())
    for parent in (un,fn):
        for n in [parent.replace('_l','_twist_01_l'),parent.replace('_l','_twist_02_l')]:
            if n in p:
                carried=p[parent]@old[parent].inverted()@old[n]
                coherent=p[parent]@rest[parent].inverted()@rest[n]
                p[n]=mix(carried,coherent,weight)
    p[hn]=H

for job in sources:
    key='/'.join(job[k] for k in ('gun','magazine','family','clip'))
    if selected and not any(key.startswith(x) for x in selected):continue
    if key in receipt:continue
    path=Path(job['source'][0]);source=path.with_suffix('.blend')
    if not source.exists():source=path.parent.parent/(path.stem+'.blend')
    if not source.exists():raise RuntimeError('Missing authoring source '+str(path))
    bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
    if r.name not in s.objects:s.collection.objects.link(r)
    r.hide_set(False);r.hide_viewport=False;r.data.pose_position='POSE'
    old_action=r.animation_data.action
    if old_action is None:raise RuntimeError('Missing active source action '+str(source))
    r.animation_data.action_slot=old_action.slots[0]
    start,end=old_action.frame_range;fps=120
    s.render.fps=fps;s.render.fps_base=1.;s.frame_start=round(start);s.frame_end=round(end)
    if job['gun']=='A762' and abs((end-start)/fps-job['seconds'])>.01:
        raise RuntimeError('Source timebase differs from live clip '+key)
    fit=fits[job['gun']];grasp=Matrix(fit['hand_in_mag'])
    finger={n:Quaternion(q) for n,q in fit['finger_basis'].items()}
    names=['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']+list(finger)
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
    lr={n:rest[parents[n]].inverted()@rest[n] for n in names}
    old_curves={fc.data_path+'#'+str(fc.array_index):fc for la in old_action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
    frames=sorted({float(k.co.x) for k in old_curves['pose.bones["hand_l"].rotation_quaternion#0'].keyframe_points})
    # Keep source key cadence (AKM extended base is already sampled at 240 Hz).
    finish=272 if job['clip']=='reload_empty' else 284
    poses={}
    for f in frames:
        if f<18 or f>finish:continue
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
        p={b.name:b.matrix.copy() for b in r.pose.bones};base={n:r.pose.bones[n].matrix_basis.copy() for n in names}
        entry=smooth((f-18)/28);release=smooth((f-248)/(finish-248))
        H=p['WPN_SOCKET_Magazine']@grasp
        # Settle, open fingers, clear the shell, then follow the original return.
        if f>240:
            H.translation+=p['WPN_SOCKET_Magazine'].to_3x3()@Vector((.012*smooth((f-240)/12),.006*smooth((f-240)/12),0))
        H=mix(p['hand_l'],H,entry);H=mix(H,p['hand_l'],release)
        weight=entry*(1-release);solve_arm(p,H,rest,weight)
        row={}
        for n in names:
            loc,q,scale=base[n].decompose()
            if n in finger:
                delay={'thumb':0,'index':1.5,'middle':2.5,'ring':3.5,'pinky':4.5}[n.split('_')[0]]
                close=smooth((f-20-delay)/24)
                target=finger[n]
                opening=smooth((f-237)/13)
                if opening:target=target.slerp(Quaternion(),opening*.38)
                q=q.slerp(target,close*(1-release))
            else:
                m=lr[n].inverted()@p[parents[n]].inverted()@p[n]
                q=m.to_quaternion()
                # Native local offsets are retained for every arm and finger.
            row[n]=q.copy()
        poses[f]=row
    action=old_action.copy();action.name=path.stem+'_MagazineGrip20260922';action.use_fake_user=True
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    curves={fc.data_path+'#'+str(fc.array_index):fc for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
    for n in names:
        fc=[curves[f'pose.bones["{n}"].rotation_quaternion#{axis}'] for axis in range(4)]
        previous=None
        for i,k in enumerate(fc[0].keyframe_points):
            f=float(k.co.x);q=poses[f][n].copy() if f in poses else Quaternion([c.keyframe_points[i].co.y for c in fc])
            if previous is not None and previous.dot(q)<0:q.negate()
            previous=q.copy()
            for axis,c in enumerate(fc):c.keyframe_points[i].co.y=q[axis];c.keyframe_points[i].interpolation='LINEAR'
        for c in fc:c.update()
    dest=O/job['gun']/job['magazine']/job['family'];dest.mkdir(parents=True,exist_ok=True)
    s.frame_set(148);bpy.context.view_layer.update()
    # Library-only A762 sources need the unchanged native hands for editing.
    if 'SK_Manny_Arms_Export' not in s.objects:
        with bpy.data.libraries.load(str(S/'AKMReloadPolish20260911/base/A_AKM_reload.blend'),link=False) as (src,dst):
            dst.objects=['SK_Manny_Arms_Export']
        skin=dst.objects[0];s.collection.objects.link(skin);skin.parent=r
        for mod in skin.modifiers:
            if mod.type=='ARMATURE':mod.object=r
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(path.stem+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    rate=round(fps/(frames[1]-frames[0]))
    bpy.ops.export_scene.fbx(filepath=str(dest/(path.stem+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=fps/rate,bake_anim_simplify_factor=0)
    receipt[key]={**job,'original_blend':str(source),'blend':str(dest/(path.stem+'.blend')),'fbx':str(dest/(path.stem+'.fbx')),
                  'fps':fps,'rate':rate,'frames':[start,end],'edit_frames':[18,finish],'hold_frames':[46,237],
                  'changed_bones':names,'weights_changed':False,'game_tested':False}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('MAGAZINE_GRASP_AUTHORED',key,flush=True)
