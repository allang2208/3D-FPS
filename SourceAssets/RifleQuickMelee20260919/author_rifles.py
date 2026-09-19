"""Adapt M4 N's stock bash and grip-centred wrist solve to each rifle's own idle.

Produces editable Blend/FBX only. No rendering or acceptance checks.
QBZ191 output is the historical N input. Its current runtime clips are authored
and imported by ../QBZ191QuickMeleeGrip20260919O; do not publish these old QBZ FBXs.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;S=P.parent
sys.path.insert(0,str(S/'M4QuickMeleeRefine20260919K'))
from arm_support import ArmSupport
sys.path.insert(0,str(S/'M4QuickMeleeRefine20260919N'))
from natural_wrist import NaturalWrist,smooth
specs=json.loads((S/'RifleTacticalSprint20260915/sources.json').read_text())
sources=json.loads((S/'RifleTacticalSprint20260915/source-poses.json').read_text())
specs['ASH12']={'mesh':'/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface','profiles':{'Base':None}}
sources['ASH12:Base']={'source':'ASH1220260917/ASH12_Editable.blend','action':'ASH12_idle'}
report={'reference':'M4QuickMeleeRefine20260919N','duration':.9,'contact':1/6,'weapons':{},'testing':'Not performed; user testing'}

def load_idle(path,action_name):
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='POSE'
    action=bpy.data.actions[action_name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene=bpy.context.scene;scene.frame_set(0);bpy.context.view_layer.update()
    return rig,scene,{b.name:b.matrix.copy() for b in rig.pose.bones}

# Cache the accepted donor once, before opening any target source.
dr,ds,donor_idle=load_idle(S/'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend','M4_QuickCombatRefineN_Base')
donor=[]
for f in range(109):
    ds.frame_set(f);bpy.context.view_layer.update()
    donor.append(dr.pose.bones['WPN_root'].matrix.copy() @ donor_idle['WPN_root'].inverted())
grip_in_hand=donor_idle['hand_r'].inverted() @ donor_idle['WPN_root']
pivot_in_hand=grip_in_hand @ Vector((0,.025,-.045))
axis_in_hand=(grip_in_hand.to_3x3() @ Vector((0,-.48,.877))).normalized()
donor_stock_idle=donor_idle['WPN_root'] @ Vector((0,.235,.025))

def stock_point(rig,idle):
    """Read the rear end of the visible weapon surface for its strike probe."""
    dg=bpy.context.evaluated_depsgraph_get();points=[]
    rootinv=idle['WPN_root'].inverted() @ rig.matrix_world.inverted()
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or ob.hide_render or not any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers):continue
        groups={g.index:g.name for g in ob.vertex_groups}
        ev=ob.evaluated_get(dg);mesh=ev.to_mesh()
        for v in mesh.vertices:
            if v.groups and groups.get(max(v.groups,key=lambda g:g.weight).group,'').startswith('WPN_'):
                points.append(rootinv @ ev.matrix_world @ v.co)
        ev.to_mesh_clear()
    if not points:raise RuntimeError('No visible weapon surface for stock anchor')
    barrel=(idle['WPN_root'].inverted() @ idle['WPN_SOCKET_Muzzle']).translation.normalized()
    rear=min(v.dot(barrel) for v in points)
    rim=[v for v in points if v.dot(barrel)<rear+.005]
    return sum(rim,Vector())/len(rim)

for weapon,spec in specs.items():
    wr={'mesh':spec['mesh'],'profiles':{}};report['weapons'][weapon]=wr
    for profile in spec['profiles']:
        info=sources[weapon+':'+profile]
        source=S/info['source'];rig,scene,idle=load_idle(source,info['action'])
        rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
        parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones};names=list(rest)
        lr={n:rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
        if profile=='Base':
            stock=stock_point(rig,idle)
            wr['stock_author_m']=list(stock)
            wr['stock_ue_cm']=[100*stock.x,-100*stock.y,100*stock.z]
        support=ArmSupport(rig,idle)
        natural=NaturalWrist(idle,rest,support.stations)
        hand_in_root=idle['WPN_root'].inverted() @ idle['hand_r']
        natural.pivot=hand_in_root @ pivot_in_hand
        natural.grip_axis=(hand_in_root.to_3x3() @ axis_in_hand).normalized()
        # The accepted movement is transported around this rifle's fitted
        # bearing wrist, rather than copying M4's absolute root and hand poses.
        shift=idle['hand_r'].translation-donor_idle['hand_r'].translation
        own_stock=Vector(wr['stock_author_m'])
        stock_initial=idle['WPN_root'] @ own_stock
        right_children=[b.name for b in rig.data.bones['hand_r'].children_recursive]
        rows=[];previous={}
        for f in range(109):
            t=f/120;weight=smooth(t/.1)*(1-smooth((t-.72)/.146666667))
            pose={n:m.copy() for n,m in idle.items()}
            if 0<f<104:
                delta=Matrix.Translation(shift) @ donor[f] @ Matrix.Translation(-shift)
                # Match the moving end of the weapon. A bullpup's butt is much
                # farther behind its root; copying a wrist trajectory alone
                # would place its striking surface somewhere else on screen.
                desired_stock=donor[f] @ donor_stock_idle
                offset_at_idle=stock_initial-donor_stock_idle
                stock_target=desired_stock+offset_at_idle*(1-weight)
                delta.translation+=(stock_target-(delta @ stock_initial))*weight
                delta=support.fit_group(delta,weight)
                for n in names:
                    if n.startswith('WPN_'):pose[n]=delta @ idle[n]
                for side in ('r','l'):support.apply(pose,side,delta @ idle['hand_'+side],weight)
                oldhand=pose['hand_r'].copy()
                pose.update(natural.apply(pose,t))
                palm_delta=pose['hand_r'] @ oldhand.inverted()
                for n in right_children:pose[n]=palm_delta @ pose[n]
            row={}
            for n in names:
                basis=lr[n].inverted() @ (pose[parents[n]].inverted() @ pose[n] if parents[n] else pose[n])
                loc,q,scale=basis.decompose()
                if n in previous and previous[n].dot(q)<0:q.negate()
                previous[n]=q.copy();row[n]=(loc,q,scale)
            rows.append(row)
        action=bpy.data.actions.new(f'{weapon}_QuickCombat_N_{profile}');action.use_fake_user=True;rig.animation_data.action=action
        for n in names:
            b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
            for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
        bag=action.layers[0].strips[0].channelbag(action.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
        for n in names:
            for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
                for axis in range(count):
                    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(109)
                    c.keyframe_points.foreach_set('co',[v for f,row in enumerate(rows) for v in (f,row[n][field][axis])])
                    for k in c.keyframe_points:k.interpolation='LINEAR'
                    c.update()
        rig.animation_data.action_slot=action.slots[0];scene.render.fps=120;scene.render.fps_base=1
        scene.frame_start=0;scene.frame_end=108;scene.frame_set(0)
        dest=P/weapon/profile;(dest/'Animations').mkdir(parents=True,exist_ok=True)
        name=f'A_{weapon}_QuickCombat_{profile}'
        fbx=dest/'Animations'/f'{name}.fbx'
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
                                add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
                                bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
        blend=dest/f'{weapon}_QuickCombat_{profile}_Editable.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        wr['profiles'][profile]={'source':str(source),'source_action':info['action'],'action':action.name,'fbx':str(fbx),
                                 'blend':str(blend),'grip_pivot_author_m':list(natural.pivot),'grip_axis_author':list(natural.grip_axis),
                                 'asset':f'/Game/Weapons/RifleQuickMelee20260919/{weapon}/{profile}/{name}'}
        (P/'authoring.json').write_text(json.dumps(report,indent=2))
        print('RIFLE_N_EXPORTED',weapon,profile,flush=True)
