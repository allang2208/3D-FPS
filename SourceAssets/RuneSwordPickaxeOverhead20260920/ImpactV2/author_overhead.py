"""Adapt the current pickaxe overhead construction to sword grips and skeleton.

The pickaxe's trajectory, shoulder/elbow planes and continuous twist solver are
the donor. Preserve the sword's hand shapes, skin, blade frame and runtime clock.
No game, regression or acceptance render is run by this authoring entry point.
"""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).parent;ROOT=P.parents[2]
DONOR=ROOT/'SourceAssets/PickaxeSightline20260919'
SOURCE=ROOT/'SourceAssets/RuneSword20260913/ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
CFG=json.loads((DONOR/'motion.json').read_text(encoding='utf-8'))
CFG.update({'revision':'SwordPickaxeOverheadImpactV2','fps':120,
            'shoulder_top_lift_m':.115,'shoulder_forward_m':.025,
            'top_grip_roll_degrees':{'l':0,'r':0},'impact_grip_roll_degrees':{'l':0,'r':0}})
CFG['raised']['center_m']=[-.005,.315,.40]
CFG['top']['center_m']=[-.005,.30,.40]
CFG['impact']['center_m']=[-.005,.54,-.40]
CFG['follow']['center_m']=[-.005,.55,-.445]
CFG['rebound']['center_m']=[-.005,.49,-.36]
FPS=120;TOTAL=2.6
# Keep the existing 1.22..1.40 combat window. A sword sweeps through the front
# during descent; it does not inherit the pickaxe's resource-contact transaction.
TIMES=((0.,0.),(.60,.32),(1.11,.47),(1.31,.60),(1.39,.60),(1.50,.685),(TOTAL,1.16))

# Reuse only pure authoring helpers: importing the donor module would regenerate
# and replace its own accepted animation files.
names={'ease','centered','pitch_frame','key','bezier','return_frame','swing_frame',
       'arm_phase','unwrap','axial_delta','frame_rotation','solve_arm'}
tree=ast.parse((DONOR/'author_attack.py').read_text(encoding='utf-8'))
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
for fn in module.body:
    if fn.name=='solve_arm':
        for node in fn.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='shoulder' for t in node.targets):
                node.value=ast.parse('arm_shoulder(side, hand.translation, weight, lift)',mode='eval').body
exec(compile(ast.fix_missing_locations(module),str(DONOR/'author_attack.py'),'exec'),globals())

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig']
source_action=bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action=source_action;rig.animation_data.action_slot=source_action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
base_idle={b.name:b.matrix.copy() for b in rig.pose.bones}
finger_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}

# Match twist rotation stations to this sword's unchanged Manny skin, instead
# of copying the pickaxe's separately fitted skin coefficients.
arm=bpy.data.objects['SK_Manny_Arms_Export'];STATIONS={}
for side in ('l','r'):
    fore='lowerarm_'+side;wrist='hand_'+side
    axis=rest[wrist].translation-rest[fore].translation
    bins={fore:[], 'lowerarm_twist_01_'+side:[], 'lowerarm_twist_02_'+side:[]}
    coords=rig.matrix_world.inverted()@arm.matrix_world
    for v in arm.data.vertices:
        if not v.groups:continue
        group=max(v.groups,key=lambda g:g.weight)
        n=arm.vertex_groups[group.group].name
        if n in bins:bins[n].append(((coords@v.co-rest[fore].translation).dot(axis))/axis.length_squared)
    STATIONS[side]={n:(max(0.,min(1.,sorted(values)[len(values)//2])) if values else 0.) for n,values in bins.items()}
    STATIONS[side][fore]=0.

def donor_time(t):
    for (a,x),(b,y) in zip(TIMES,TIMES[1:]):
        if t<=b:return x+(y-x)*(t-a)/(b-a)
    return 1.16

def long_idle_pose(original):
    """Same 18 mm left-grip fit used by the installed modular long grip."""
    pose={n:m.copy() for n,m in original.items()}
    chain=['clavicle_l','upperarm_l','lowerarm_l','hand_l']
    points=[original[n].translation.copy() for n in chain]
    goal=points[-1]+original['WPN_root'].to_quaternion()@Vector((0,0,-.018))
    shoulder=points[1];v=goal-shoulder;direction=v.normalized()
    l1=(points[2]-shoulder).length;l2=(points[3]-points[2]).length
    along=(l1*l1-l2*l2+v.length_squared)/(2*v.length)
    bend=points[2]-shoulder;bend=(bend-direction*bend.dot(direction)).normalized()
    fitted=[points[0],shoulder,shoulder+direction*along+bend*math.sqrt(max(0.,l1*l1-along*along)),goal]
    desired={}
    for i,n in enumerate(chain):
        q=original[n].to_quaternion()
        if i<3:q=(points[i+1]-points[i]).rotation_difference(fitted[i+1]-fitted[i])@q
        desired[n]=Matrix.LocRotScale(fitted[i],q,original[n].decompose()[2])
    # Non-chain children retain their original local matrices, like the runtime
    # long-grip keys; this includes the original finger and twist tracks.
    for b in rig.data.bones:
        if b.name in desired:pose[b.name]=desired[b.name]
        elif b.parent:pose[b.name]=pose[b.parent.name]@original[b.parent.name].inverted()@original[b.name]
    return pose

def fit_group(wpn, t):
    """Project the held group into both arms' reach; never stretch arm bones."""
    grip,down,lift=arm_phase(t,False)
    weight=ease(t/CFG['entry_blend_seconds'])*(1-ease((t-(1.16-CFG['exit_blend_seconds']))/CFG['exit_blend_seconds']))*grip
    if CFG['release_seconds']<t<=CFG['contact_seconds']:
        lift=max(0.,min(1.,((wpn@PIVOT).z-CFG['impact']['center_m'][2])/(CFG['top']['center_m'][2]-CFG['impact']['center_m'][2])))
    fitted=wpn.copy()
    for _ in range(12):
        for side in ('l','r'):
            hand=(fitted@grips[side]).translation
            shoulder=arm_shoulder(side,hand,weight,lift)
            l1=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
            l2=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
            delta=hand-shoulder;maximum=l1+l2-.007
            if delta.length>maximum:fitted.translation-=delta.normalized()*(delta.length-maximum)
    return fitted,weight,down,lift

def arm_shoulder(side,hand,weight,lift):
    """Keep both elbows softly extended through the working part of the chop.

    Unshrug/settle the shoulder by at most 5.5 cm when a closer hand would leave
    its elbow folded. Exact segment lengths, wrist and sword grips stay fixed.
    """
    sign=1 if side=='r' else -1
    shoulder=idle['upperarm_'+side].translation+Vector((sign*CFG['shoulder_outward_m'],
        CFG['shoulder_forward_m'],.005+(CFG['shoulder_top_lift_m']-.005)*lift))*weight
    l1=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
    l2=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
    delta=shoulder-hand
    wanted=math.sqrt(l1*l1+l2*l2-2*l1*l2*math.cos(math.radians(156.)))
    if delta.length<wanted:
        shoulder+=delta.normalized()*min(.055,(wanted-delta.length))*weight
    return shoulder

report={'revision':CFG['revision'],'donor':str(DONOR),'sword_source':str(SOURCE),'seconds':TOTAL,
        'contact_window':[1.22,1.40],'time_map':TIMES,'skin_stations':STATIONS,'variants':[],
        'runtime_tested':False,'acceptance_rendered':False}
for variant in ('Standard','LongGrip'):
    idle=long_idle_pose(base_idle) if variant=='LongGrip' else {n:m.copy() for n,m in base_idle.items()}
    ready=idle['WPN_root'].copy()
    grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
    # The donor pivot is between the two palms. Rebuild it on this actual hilt;
    # the sword's +Z blade direction and hand order remain intact.
    PIVOT=Vector((0,0,(grips['l'].translation.z+grips['r'].translation.z)*.5))
    READY_CENTER=ready@PIVOT
    RAISED,TOP,IMPACT,FOLLOW,REBOUND=[key(k) for k in ('raised','top','impact','follow','rebound')]
    name='A_RuneSword_Overhead';action=bpy.data.actions.new(name+'_'+variant)
    action.use_fake_user=True;rig.animation_data.action=action
    scene.render.fps=FPS;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=round(TOTAL*FPS)
    previous={};state={};rows=[]
    for frame in range(scene.frame_end+1):
        t=frame/FPS;dt=donor_time(t);scene.frame_set(frame)
        pose={n:m.copy() for n,m in idle.items()}
        if 0<t<TOTAL:
            wpn,weight,down,lift=fit_group(swing_frame(dt),dt)
            for side in ('l','r'):
                # Fixed sword-local grasp, including all original finger joints.
                solve_arm(pose,side,wpn@grips[side],weight,down,lift,state)
            pose['WPN_root']=wpn
            for bone in ('Blade_Base','Blade_Tip'):
                # Sword-specific trace markers must follow the held blade too;
                # the pickaxe donor has no equivalent blade marker tracks.
                if bone in pose:pose[bone]=wpn@idle['WPN_root'].inverted()@idle[bone]
        keys={}
        for bone in rig.pose.bones:
            pinv=pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
            bone.matrix_basis=local_rest[bone.name].inverted()@pinv@pose[bone.name]
            bone.rotation_mode='QUATERNION';q=bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
            bone.rotation_quaternion=q;previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=frame,group=bone.name)
            keys[bone.name]={'location':list(bone.location),'quaternion_wxyz':list(q),'scale':list(bone.scale)}
        rows.append({'seconds':t,'donor_seconds':dt,'bones':keys})
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for k in curve.keyframe_points:k.interpolation='LINEAR'
    output=P/variant;output.mkdir(exist_ok=True)
    (output/'editable_keys.json').write_text(json.dumps({'fps':FPS,'seconds':TOTAL,'samples':rows},separators=(',',':')),encoding='utf-8')
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(output/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'Sword_PickaxeOverhead_Editable.blend'))
    report['variants'].append({'name':variant,'grips':{s:[list(r) for r in g] for s,g in grips.items()},'fbx':str(output/(name+'.fbx'))})
    print('SWORD_PICKAXE_OVERHEAD_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
