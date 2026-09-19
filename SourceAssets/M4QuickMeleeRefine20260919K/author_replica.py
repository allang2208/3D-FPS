"""Bake the reference reconstruction into M4's six existing grip profiles."""
import ast,bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;S=P.parent
sys.path.insert(0,str(P))
from arm_support import ArmSupport
data=json.loads((P/'motion_frames.json').read_text())
tree=ast.parse((S/'RifleStockMelee20260918/author_quickcombat.py').read_text(encoding='utf-8'))
sources=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(sources)
receipt={'revision':'HingeShoulderRefineK','duration':data['duration'],'contact':data['contact'],'profiles':{},'testing':'Not performed; user testing'}
def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

for profile in args:
    filename,clip=sources[profile];source=S/filename
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.open_mainfile(filepath=str(source))
    rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='POSE';scene=bpy.context.scene
    action=bpy.data.actions[clip];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_set(0);bpy.context.view_layer.update()
    names=[b.name for b in rig.data.bones];parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
    idle={b.name:b.matrix.copy() for b in rig.pose.bones}
    if profile in ('Base','Drum'):
        shift=idle['WPN_root'].to_3x3()@Vector((0,-.032 if profile=='Drum' else -.012,0))
        for n in names:
            a=n
            while a and a!='clavicle_l':a=parents[a]
            if a or n=='ik_hand_l':idle[n].translation+=shift
    support=ArmSupport(rig,idle)

    frames=[];rows=[];previous={}
    for sample in data['frames']:
        t=sample['time'];frames.append(sample['frame']);p={n:m.copy() for n,m in idle.items()}
        delta=Matrix(sample['weapon_delta']);weight=smooth(t/.10)*(1-smooth((t-.72)/.146666667))
        delta=support.fit_group(delta,weight)
        for n in names:
            if n.startswith('WPN_'):p[n]=delta@idle[n]
        if weight>0 or 0<t<data['duration']:
            for side in ('r','l'):support.apply(p,side,delta@idle['hand_'+side],weight)
        row={}
        for n in names:
            basis=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            loc,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    a=bpy.data.actions.new('M4_QuickCombatRefineK_'+profile);a.use_fake_user=True;rig.animation_data.action=a
    for n in names:
        b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
    bag=a.layers[0].strips[0].channelbag(a.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
    for n in names:
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
                for k in c.keyframe_points:k.interpolation='LINEAR'
                c.update()
    rig.animation_data.action_slot=a.slots[0];scene.render.fps=120;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=frames[-1];scene.frame_set(0)
    dest=P/profile;(dest/'Animations').mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx=dest/'Animations'/f'A_M4_QuickCombat_{profile}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/f'M4_QuickCombat_{profile}_Editable.blend'))
    receipt['profiles'][profile]={'source':str(source),'source_action':clip,'action':a.name,'fbx':str(fbx),'skin_stations':support.stations,'support':support.parameters}
    print('M4_REFERENCE_REPLICA_EXPORTED',profile,flush=True)
(P/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
