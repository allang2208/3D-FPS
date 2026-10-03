"""Retarget the left support anchor without altering the right-hand bolt action."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
inputs=json.loads((O/'support_input.json').read_text());sources=json.loads((O/'sources.json').read_text())
draft='--draft' in sys.argv
bpy.context.preferences.filepaths.save_version=0
# The existing native fore-end grip supplies the palm and grouped fingers.
target=Matrix(inputs['poses']['450']['hand_in_root']);target.translation+=Vector((0,.035,0))
finger_basis=inputs['poses']['450']['basis']
if (O/'fitted_support.json').exists():
    fitted=json.loads((O/'fitted_support.json').read_text())
    if not fitted['success']:raise RuntimeError('Body contact fit is not ready')
    target=Matrix(fitted['hand_in_root']);finger_basis=fitted['finger_basis']
solver=(S/'RifleMagazineGrip20260922/build_animations.py').read_text()
solver=solver[solver.index('def smooth('):solver.index('for job in sources:')]
exec(compile(solver,str(O/'native_arm_solver'),'exec'))
arm=['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']
receipt={}
diagnosis={}
hand_names=json.loads((S/'RifleMagazineGrip20260922/fit_input.json').read_text())['names']
geometry_names=json.loads((O/'source_motion.json').read_text())['weapon_objects']
for info in sources['animations'][:1] if draft else sources['animations']:
    source=Path(info['source'][0]).with_suffix('.blend')
    bpy.ops.wm.open_mainfile(filepath=str(O/'Support_Working.blend') if info['family']=='base' else str(source))
    s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];old=r.animation_data.action
    if info['family']!='base':
        for ob in s.objects:
            if ob.type=='MESH':ob.hide_render=ob.name!='SK_Manny_Arms_Export'
        with bpy.data.libraries.load(str(O/'Support_Working.blend'),link=False) as (src,dst):
            dst.objects=[n for n in geometry_names if n in src.objects]
        for ob in dst.objects:
            if ob.name not in s.objects:s.collection.objects.link(ob)
            world=ob.matrix_world.copy();ob.parent=r;ob.matrix_world=world
            for modifier in ob.modifiers:
                if modifier.type=='ARMATURE':modifier.object=r
            ob.hide_set(False);ob.hide_render=False
    fingers=[n for n in finger_basis if n.startswith(('thumb','index','middle','ring','pinky'))]
    names=arm+fingers
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
    lr={n:rest[parents[n]].inverted()@rest[n] for n in names}
    curves=lambda a:{fc.data_path+'#'+str(fc.array_index):fc for la in a.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
    oldcurves=curves(old);frames=[float(k.co.x) for k in oldcurves['pose.bones["hand_l"].rotation_quaternion#0'].keyframe_points]
    poses={}
    for f in frames:
        if not 254<f<440:continue
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
        p={b.name:b.matrix.copy() for b in r.pose.bones};original={n:r.pose.bones[n].matrix_basis.copy() for n in names}
        weight=smooth((f-254)/18)*(1-smooth((f-385)/55))
        H=mix(p['hand_l'],p['WPN_root']@target,weight);solve_arm(p,H,rest,weight)
        row={}
        for n in names:
            if n in fingers:q=original[n].to_quaternion().slerp(Quaternion(finger_basis[n]),weight)
            else:q=(lr[n].inverted()@p[parents[n]].inverted()@p[n]).to_quaternion()
            row[n]=q.copy()
        poses[f]=row
    action=old.copy();action.name=source.stem+'_A762BodySupport';action.use_fake_user=True
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];newcurves=curves(action)
    for n in names:
        tracks=[newcurves[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)];previous=None
        for index,k in enumerate(tracks[0].keyframe_points):
            f=float(k.co.x);q=poses[f][n].copy() if f in poses else Quaternion([c.keyframe_points[index].co.y for c in tracks])
            if previous is not None and previous.dot(q)<0:q.negate()
            previous=q.copy()
            for axis,c in enumerate(tracks):c.keyframe_points[index].co.y=q[axis];c.keyframe_points[index].interpolation='LINEAR'
        for c in tracks:c.update()
    s.frame_set(320);bpy.context.view_layer.update()
    if draft:
        bpy.ops.wm.save_as_mainfile(filepath=str(O/'Support_Draft.blend'))
        break
    frame_samples=sorted(set(list(range(254,273,2))+list(range(272,386,4))+list(range(385,441,5))+[320,330,345,440]))
    rows={}
    for f in frame_samples:
        s.frame_set(f);bpy.context.view_layer.update();inverse_root=r.pose.bones['WPN_root'].matrix.inverted()
        rows[str(f)]={n:[list(row) for row in inverse_root@r.pose.bones[n].matrix] for n in hand_names}
    allowed={f'pose.bones["{n}"].rotation_quaternion#{i}' for n in names for i in range(4)}
    other_changes=[]
    for curve_key,a in oldcurves.items():
        if curve_key in allowed:continue
        b=newcurves[curve_key]
        if len(a.keyframe_points)!=len(b.keyframe_points) or any(x.co!=y.co for x,y in zip(a.keyframe_points,b.keyframe_points)):
            other_changes.append(curve_key)
    diagnosis[info['family']]={'poses':rows,'changes_outside_left_rotation_tracks':other_changes}
    (O/'source_pose_diagnosis.json').write_text(json.dumps(diagnosis),encoding='utf-8')
    s.frame_set(320)
    dest=O/info['family'];dest.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(source.stem+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(dest/(source.stem+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    receipt[info['family']]={**info,'gun':'A762','clip':'reload_empty','magazine':'standard_and_extended',
        'original_blend':str(source),'blend':str(dest/(source.stem+'.blend')),'fbx':str(dest/(source.stem+'.fbx')),
        'fps':120,'rate':120,'frames':list(action.frame_range),'changed_bones':names,'edit_frames':[254,440],
        'support_frames':[272,385],'weights_changed':False,'game_tested':False}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('A762_SUPPORT_AUTHORED',info['family'],flush=True)
(O/'support_target.json').write_text(json.dumps({'hand_in_root':[list(row) for row in target],
    'finger_basis':{n:finger_basis[n] for n in fingers},'edit_frames':[254,440],'hold_frames':[272,385]},indent=2),encoding='utf-8')
