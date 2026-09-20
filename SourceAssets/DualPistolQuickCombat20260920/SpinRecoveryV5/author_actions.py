"""Build three complete recovery profiles from the accepted V3 strike.

Blender --background --python author_actions.py -- M1911|DW715
Creates editable source and FBX only; no tests, renders or game launches.
"""
import ast,json,math,sys
from pathlib import Path
import bpy
from mathutils import Euler,Matrix,Quaternion,Vector
OUT=Path(__file__).parent;BASE=OUT.parent;REVISION='SpinRecoveryV5'
SOURCE=BASE.parent/'PistolDualWield20260914/NaturalAimV3'
WEAPON=sys.argv[sys.argv.index('--')+1]
RIG_NAME={'M1911':'SK_M1911_Manny','DW715':'SK_DW715_Manny'}[WEAPON]
MOTION=json.loads((BASE/'VideoRefV3/motion.json').read_text())
GEOMETRY=json.loads((OUT/'author_geometry.json').read_text())
sys.path.insert(0,str(OUT))
from recovery_solver import PROFILES,window,natural_hand,support_twist,relax_fingers,spin_gun
# Import pure V3 helpers only; never execute/rewrite the original author assets.
tree=ast.parse((BASE/'VideoRefV3/author_actions.py').read_text())
functions={'camera','turn','source_keyed','keyed','envelope','flow_tangents','solve_arm'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions],type_ignores=[]),'V3_helpers','exec'),globals())
FLOW_TANGENTS={(s,c):flow_tangents(MOTION[s]['times'],MOTION[s][c]) for s in ('r','l') for c in ('position','angles','shoulder','elbow')}
receipt={'weapon':WEAPON,'revision':REVISION,'duration':.8,'contact':.18,'sample_rate':120,'loop':False,
         'profiles':PROFILES,'sides':{},'testing':'Not performed; user testing'}
for side in ('r','l'):
    source=SOURCE/WEAPON/side/f'{WEAPON}_{side}_Dual_Editable.blend'
    bpy.context.preferences.filepaths.save_version=0
    try:bpy.ops.wm.open_mainfile(filepath=str(source))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e):raise
    scene=bpy.context.scene;scene.render.fps=60;rig=bpy.data.objects[RIG_NAME];rig.data.pose_position='POSE';rig.animation_data_create()
    names=[b.name for b in rig.data.bones];parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
    destination=OUT/WEAPON/side;(destination/'Animations').mkdir(parents=True,exist_ok=True)
    clips={};actions={}
    for profile_name,profile in PROFILES.items():
      for LEAD,empty in [(lead,empty) for lead in ('r','l') for empty in ([False,True] if WEAPON=='M1911' else [False])]:
        suffix='_empty' if empty else '';idle_name=f'Dual_{WEAPON}_{side}_idle{suffix}'
        idle_action=bpy.data.actions[idle_name];rig.animation_data.action=idle_action;rig.animation_data.action_slot=idle_action.slots[0]
        scene.frame_set(0);bpy.context.view_layer.update();idle={b.name:b.matrix.copy() for b in rig.pose.bones}
        grip=idle['WPN_root'].inverted()@idle['hand_'+side]
        gun_local={n:idle['WPN_root'].inverted()@idle[n] for n in names if n.startswith('WPN_')}
        rows=[];frames=[];previous={};state={};count=96
        for i in range(count+1):
            t=i/120.;p={n:m.copy() for n,m in idle.items()}
            lead=side==LEAD;sign=1. if side=='r' else -1.
            sample=t if lead else t-.055*window(t,.30,.44,.64,.79)
            position=keyed(side,'position',sample);angles=keyed(side,'angles',sample)
            swing_weight=window(t,.32,.445,.66,.765) if lead else window(t,.36,.48,.68,.785)
            if lead:
                position+=Vector((profile['forward'],sign*profile['outward'],.008))*swing_weight
            pivot=idle['hand_'+side].translation
            transform=Matrix.Translation(pivot+camera(position))@turn(angles).to_matrix().to_4x4()@Matrix.Translation(-pivot)
            root=transform@idle['WPN_root'];hand=root@grip
            shoulder=idle['upperarm_'+side].translation+camera(keyed(side,'shoulder',sample))
            pole=idle['lowerarm_'+side].translation+camera(keyed(side,'elbow',sample))
            if i not in (0,count):
                if swing_weight>0:
                    # Shoulder, elbow and palm work together; preserve the
                    # exact gun-local grip before release and after catching.
                    shoulder+=camera((.008,sign*.010,0))*swing_weight
                    hand,shoulder,pole=natural_hand(idle,rest,side,hand,shoulder,pole,swing_weight)
                    root=hand@grip.inverted()
                solve_arm(p,idle,side,hand,shoulder,pole,names)
                support_twist(p,idle,rest,side,GEOMETRY[WEAPON][side]['skin_stations'],swing_weight,state)
                if lead:
                    relax_fingers(p,idle,side,t,profile,parents,local_rest)
                    root=spin_gun(root,p,idle,rest,side,t,profile,WEAPON,camera)
            for n,local in gun_local.items():p[n]=root@local
            row={}
            for n in names:
                local=p[parents[n]].inverted()@p[n] if parents[n] else p[n]
                loc,q,scale=(local_rest[n].inverted()@local).decompose()
                if n in previous and previous[n].dot(q)<0:q.negate()
                previous[n]=q.copy();row[n]=(loc,q,scale)
            rows.append(row);frames.append(t*60)
        kind='quickcombat'+('_left' if LEAD=='l' else '')+profile['suffix']+suffix
        action=bpy.data.actions.new(f'Dual_{WEAPON}_{side}_{kind}');action.use_fake_user=True;rig.animation_data.action=action
        for n in names:
            b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
            for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
        curves={(c.data_path,c.array_index):c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
        for n in names:
            for prop,field,size in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
                for axis in range(size):
                    curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(frames))
                    curve.keyframe_points.foreach_set('co',[v for frame,row in zip(frames,rows) for v in (frame,row[n][field][axis])])
                    for k in curve.keyframe_points:k.interpolation='LINEAR'
                    curve.update()
        rig.animation_data.action_slot=action.slots[0];scene.frame_start=0;scene.frame_end=48;scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        fbx=destination/'Animations'/f'A_Dual_{WEAPON}_{side}_{kind}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
            add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
        clips[kind]={'fbx':str(fbx),'idle':idle_name,'striking_hand':LEAD,'profile':profile_name};actions[kind]=action
        print('DUAL_SPIN_RECOVERY_EXPORTED '+WEAPON+'/'+side+'/'+kind,flush=True)
    rig.animation_data.action=actions['quickcombat'];rig.animation_data.action_slot=actions['quickcombat'].slots[0];scene.frame_set(0)
    blend=destination/f'{WEAPON}_{side}_QuickCombat_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    receipt['sides'][side]={'source':str(source),'blend':str(blend),'clips':clips}
(OUT/f'{WEAPON}-authoring.json').write_text(json.dumps(receipt,indent=2))
print('DUAL_SPIN_RECOVERY_AUTHOR_COMPLETE '+WEAPON,flush=True)
