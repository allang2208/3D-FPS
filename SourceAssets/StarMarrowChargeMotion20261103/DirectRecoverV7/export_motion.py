"""Export deterministic, installed-idle-aligned anatomical poses; never solve IK again."""
from pathlib import Path
import bpy,json,sys
from mathutils import Matrix

P=Path(__file__).resolve().parent;ROOT=P.parent.parents[1]
sys.path.insert(0,str(ROOT/'SourceAssets/RuneSword20260913/InspectReverseV85'))
import v85_keys,v85_setup
variant='LongGrip' if '--long-grip' in sys.argv else 'Standard'
data=json.loads((P/variant/'poses.json').read_text())
c=v85_setup.load(variant);rig=c.rig
action=bpy.data.actions.new('A_StarMarrow_Charge');rig.animation_data.action=action
previous={}
for frame,row in enumerate(data['poses']):
    pose={n:Matrix(m) for n,m in zip(data['names'],row)}
    for n in data['names']:
        b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
        parent=pose.get(c.parent[n],Matrix.Identity(4))
        loc,q,scale=(c.local_rest[n].inverted()@parent.inverted()@pose[n]).decompose()
        if n in previous and q.dot(previous[n])<0:q.negate()
        previous[n]=q.copy();b.location,b.rotation_quaternion,b.scale=loc,q,scale
        for channel in ('location','rotation_quaternion','scale'):
            b.keyframe_insert(channel,frame=frame,group=n)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
c.scene.render.fps=data['fps'];c.scene.render.fps_base=1.
c.scene.frame_start=0;c.scene.frame_end=len(data['poses'])-1;c.scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
out=P/variant;out.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(out/'A_StarMarrow_Charge.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'StarMarrow_Charge.blend'))
(out/'authoring.json').write_text(json.dumps(dict(variant=variant,revision=7,
    seconds=data['seconds'],fps=data['fps'],frames=len(data['poses']),
    source='DirectRecoverV7/solve_motion.py',idle='actual installed idle, no second IK handoff',
    fixed_bone_lengths=True,continuous_elbow_hinges=True,
    camera_release_seconds=1.64,gameplay_tested=False),indent=2))
print('ANATOMICAL_CHARGE_EXPORTED',variant)
