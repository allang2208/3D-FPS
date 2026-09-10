import bpy,math,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_reload_empty'];assert not a.get('natural_entry_clearance_applied',False);r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
# Cache first, so updated keys cannot change subsequent source samples.
poses=[]
for k in range(35*8,38*8+1):
 f=k/8;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();b=r.pose.bones['clavicle_l'];m=b.matrix.copy();w=smooth(f-35)*(1-smooth(f-37));m.translation+=r.pose.bones['WPN_SOCKET_Magazine'].matrix.to_3x3()@Vector((.090*w,0,0));poses.append((f,m))
for f,m in poses:
 s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();b=r.pose.bones['clavicle_l'];b.matrix=m;b.keyframe_insert('location',frame=f)
a['natural_entry_clearance_applied']=True;s.render.fps=60;s.frame_start=0;s.frame_end=162;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'A_M4_MAT_reload_empty.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
s.frame_set(80);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));print('NATURAL_ENTRY_CLEARANCE_APPLIED')
