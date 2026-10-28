"""V8: short loading arc and late acceleration; preserve V7 contact/recovery.

One shared native-bow clip. Confirmed-contact recoil is applied to the complete
runtime pose, so no second full hit-animation variant is needed.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

P=Path(__file__).parent
PRIOR=P.parent/'BowQuickCombatRecover20260927'
source=PRIOR/'author_recover.py'
prior={'__file__':str(source)}
exec(compile(source.read_text().split('\nbpy.ops.wm.open_mainfile')[0],str(source),'exec'),prior)
for key in ('order','parent','L','G','mat','world_to_blender','timing'):
    globals()[key]=prior[key]
palm=prior['palm']
old_bow=palm['bow_at']
C=timing['Cock'];HIT=timing['Contact']
FPS=240
OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)

def ease(t):
    t=max(0.,min(1.,t))
    return t*t*t*(10.+t*(-15.+6.*t))

def bow_at(t):
    bow=old_bow(t)
    if t<=G or t>=HIT:return bow
    if t<C:
        load=ease((t-G)/(C-G))
        arc=0.
    else:
        u=(t-C)/(HIT-C)
        # Retain the short loaded pose longer, then accelerate into the same
        # contact. Both ends have zero offset velocity, preserving continuity.
        load=1.-ease(u*u)
        arc=math.sin(math.pi*u)**2
    location=bow.translation+Vector((-2.5*load,.65*load,.8*load+.65*arc))
    rotation=Matrix.Rotation(math.radians(5.*load),3,'Z')@bow.to_3x3()
    return mat(location,rotation)

# V5 solves both arm chains against these same moving palm/grip frames; V6
# then supplies its relaxed wrist, and V7 retains its unchanged recovery.
palm['bow_at']=bow_at
pose=prior['pose']
bpy.ops.wm.open_mainfile(filepath=str(PRIOR/'Bow_QuickCombat.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Bow_V7_Native'];arm=rig.data
scene=bpy.context.scene;scene.render.fps=FPS
rig.animation_data_create()
rig.animation_data.action=bpy.data.actions.new('A_Bow_QuickCombat_ImpactV8')
scene.frame_start=0;scene.frame_end=round(L*FPS)
last={}
for frame in range(scene.frame_end+1):
    world=pose(frame/FPS)
    for n in order:
        bone=rig.pose.bones[n]
        relative=world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
        restlocal=arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
        bone.rotation_mode='QUATERNION';bone.matrix_basis=restlocal.inverted()@relative
        if frame and bone.rotation_quaternion.dot(last[n])<0:bone.rotation_quaternion.negate()
        last[n]=bone.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=frame)
scene.frame_set(0);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Bow_QuickCombat.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_QuickCombat.blend'))
(P/'authoring.json').write_text(json.dumps({
    'fps':FPS,'timing_seconds':timing,'source':str(source),'load_back_cm':2.5,'load_yaw_degrees':5.,
    'asset':'/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat',
    'preserved':'V7 source clock, exact contact pose, grip frames, fingers and natural recovery',
    'runtime_recoil':'Shared whole-pose translation after confirmed contact only',
    'rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_IMPACT_AUTHORED',str(OUT/'A_Bow_QuickCombat.fbx'))
