"""V6: continue the fixed left grasp with a relaxed wrist and supporting elbow.

Only the left shoulder/arm support chain changes. The V5 open right palm,
hand-to-bow contacts, finger poses, weapon path and source clock are retained.
This is authoring/export, with no preview or acceptance run.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P=Path(__file__).parent
ROOT=P.parents[1]
PRIOR=P.parent/'BowQuickCombatPalm20260927'
script=PRIOR/'author_palm.py'
prior={'__file__':str(script)}
exec(compile(script.read_text().split('\nbpy.ops.wm.open_mainfile')[0],str(script),'exec'),prior)
for key in ('rest','local','parent','order','mat','smooth','world_to_blender',
            'limb_frame','anatomy','R','L','G','RELEASE','timing','keys'):
    globals()[key]=prior[key]
FPS=240
OUT=P/'Export'
OUT.mkdir(parents=True,exist_ok=True)
WRIST_RELAXED_BEND_DEG=12.

def pose(t):
    w=prior['pose'](t)
    support=smooth(t/G)*(1.-smooth((t-RELEASE)/(L-RELEASE)))
    if support<=0.:
        return w
    clav,up,low,hand='clavicle_l','upperarm_l','lowerarm_l','hand_l'
    wrist=w[hand].translation.copy()
    original_shoulder=w[up].translation.copy()
    original_elbow=w[low].translation.copy()
    rest_forearm=rest[hand].translation-rest[low].translation
    hand_delta=w[hand].to_3x3()@rest[hand].to_3x3().transposed()
    neutral=(hand_delta@rest_forearm).normalized()
    forearm=(wrist-original_elbow).normalized()
    angle=forearm.angle(neutral)
    target_angle=math.radians(WRIST_RELAXED_BEND_DEG)
    if angle<=target_angle:
        return w

    # Keep the hand and all its descendants exactly on their existing grasp.
    # Bring the forearm towards its rest-compatible hand direction, leaving a
    # small natural bend instead of pushing the back of the wrist upwards.
    turn=forearm.rotation_difference(neutral)
    identity=turn.copy()
    identity.identity()
    fraction=(1.-target_angle/angle)*support
    direction=(identity.slerp(turn,fraction)@forearm).normalized()
    l1=local[low].translation.length
    l2=local[hand].translation.length
    elbow=wrist-direction*l2

    # Recruit the shoulder by the shortest displacement compatible with this
    # elbow and the native upper-arm length. No segment scaling or wrist shift.
    shoulder=elbow+(original_shoulder-elbow).normalized()*l1
    old_upper=(original_elbow-original_shoulder).normalized()
    new_upper=(elbow-shoulder).normalized()
    swing=old_upper.rotation_difference(new_upper)
    upper_rotation=swing.to_matrix()@w[up].to_3x3()
    across=R@Vector(anatomy['l']['across'])
    lower_delta=limb_frame(direction,hand_delta@across)@limb_frame(rest_forearm,across).transposed()
    w[clav].translation=shoulder-w[clav].to_3x3()@local[up].translation
    w[up]=mat(shoulder,upper_rotation)
    w[low]=mat(elbow,lower_delta@rest[low].to_3x3())

    # Full segment transforms for the native arm helpers. Stop at hand_l:
    # accepted palm/finger transforms and bow markers remain untouched.
    moved={up,low}
    for n in order:
        if parent[n] in moved and n not in (low,hand):
            moved.add(n)
            w[n]=w[parent[n]]@local[n]
    return w

bpy.ops.wm.open_mainfile(filepath=str(PRIOR/'Bow_QuickCombat.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Bow_V7_Native']
arm=rig.data
scene=bpy.context.scene
scene.render.fps=FPS
rig.animation_data_create()
rig.animation_data.action=bpy.data.actions.new('A_Bow_QuickCombat_WristNatural')
scene.frame_start=0
scene.frame_end=round(L*FPS)
last={}
for frame in range(scene.frame_end+1):
    world=pose(frame/FPS)
    for n in order:
        b=rig.pose.bones[n]
        relative=world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
        restlocal=arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
        b.rotation_mode='QUATERNION'
        b.matrix_basis=restlocal.inverted()@relative
        if frame and b.rotation_quaternion.dot(last[n])<0:
            b.rotation_quaternion.negate()
        last[n]=b.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):
            b.keyframe_insert(prop,frame=frame)
scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Bow_QuickCombat.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_QuickCombat.blend'))
(P/'authoring.json').write_text(json.dumps({
    'fps':FPS,'timing_seconds':timing,
    'asset':'/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat',
    'source_binding':'ContactV9 / V7 native bow arms / V11 idle',
    'prior_source':str(script),
    'change':'Left forearm follows fixed grasp, with supporting elbow and shoulder',
    'left_wrist_target_bend_degrees':WRIST_RELAXED_BEND_DEG,
    'left_hand_and_fingers':'Preserved complete V5 world transforms',
    'right_hand':'Preserved V5 open palm and all entry/recovery poses',
    'bow_keys':keys,'runtime_retiming':'Unchanged, 0.570833 sec miss / 0.605833 sec hit',
    'rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_LEFT_WRIST_AUTHORED',str(OUT/'A_Bow_QuickCombat.fbx'))
