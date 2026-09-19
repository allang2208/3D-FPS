import bpy,math,json
from pathlib import Path
from mathutils import Euler,Quaternion
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();a=bpy.data.actions['M4_idle'];old=r.animation_data.action;r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();thumb={b.name:b.rotation_quaternion.copy() for b in r.pose.bones if b.name.startswith('thumb') and b.name.endswith('_l')};r.animation_data.action=old;r.animation_data.action_slot=old.slots[0];s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
for d in ['index','middle','ring','pinky']:
 r.pose.bones[d+'_metacarpal_l'].rotation_quaternion=Quaternion()
 for j,z in enumerate([20,45,25],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Euler((0,0,math.radians(z))).to_quaternion()
for n,q in thumb.items():r.pose.bones[n].rotation_quaternion=q
bpy.context.view_layer.update();a=bpy.data.actions.new('M4_NATURAL_grip');r.animation_data.action=a
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'natural_grip.blend'))
exec((O/'render_fit.py').read_text(encoding='utf-8').replace("O/'grip_fitted.blend'","O/'natural_grip.blend'").replace("f'grip_fitted_{i}.png'","f'natural_grip_{i}.png'"))
