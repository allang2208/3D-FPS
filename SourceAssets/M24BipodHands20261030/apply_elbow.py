import bpy,numpy as np,json
from mathutils import Quaternion
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'),use_scripts=False)
skin=bpy.data.objects['M24_V9_BareArms'];keys=np.load(O/'elbow_correctives.npz')
P=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data])
for name in keys.files:
    key=skin.data.shape_keys.key_blocks.get(name) or skin.shape_key_add(name=name,from_mix=False)
    key.data.foreach_set('co',(P+keys[name]/100).ravel());key.value=0
curves=json.loads((O/'elbow_curves.json').read_text())
skin.data.shape_keys.animation_data_clear()
for name,c in curves.items():
    key=skin.data.shape_keys.key_blocks[name]
    for t,value in zip(c['times'],c['values']):
        key.value=value;key.keyframe_insert('value',frame=t*200)
    key.value=0
action=skin.data.shape_keys.animation_data.action
action.name='M24_Bipod_Elbow_Curves_048'
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for k in curve.keyframe_points:k.interpolation='LINEAR'
# Keep the editable baked actions aligned with the payload's shortest-path
# quaternion interpolation, including subframes between the 200 Hz keys.
for arm_action in bpy.data.actions:
    if not arm_action.name.endswith('_HandElbow30'):continue
    for layer in arm_action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                quats={}
                for curve in bag.fcurves:
                    for k in curve.keyframe_points:k.interpolation='LINEAR'
                    if curve.data_path.endswith('.rotation_quaternion'):
                        quats.setdefault(curve.data_path,{})[curve.array_index]=curve
                for channels in quats.values():
                    if set(channels)!={0,1,2,3}:continue
                    previous=None
                    for i in range(len(channels[0].keyframe_points)):
                        q=Quaternion([channels[j].keyframe_points[i].co.y for j in range(4)])
                        if previous is not None and previous.dot(q)<0:
                            q=-q
                            for j in range(4):channels[j].keyframe_points[i].co.y=q[j]
                        previous=q
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'))
print('BIPOD_ELBOW_SOURCE_SAVED',len(keys.files),flush=True)
