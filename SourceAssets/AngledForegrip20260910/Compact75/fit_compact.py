import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;OLD=O.parent/'GameIntegration'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'A_M4_Foregrip_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update()
f=json.loads((OLD/'fit_final.json').read_text());root=r.pose.bones['WPN_root'].matrix.copy();G=root@Matrix(f['grip_in_root']);anchor=G@Vector((0,0,.595));S=Matrix.Translation(anchor)@Matrix.Scale(.75,4)@Matrix.Translation(-anchor);NG=S@G
# Keep original attachment anchor; scale geometry only, never the hands or skeleton.
for ob in [x for x in s.objects if x.name.startswith('FG_')]:
 world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=S@world
H=r.pose.bones['hand_l'].matrix.copy();middle=r.pose.bones['middle_01_l'].head.copy();H.translation+=(S@middle-middle)
r.animation_data.action=None;r.pose.bones['hand_l'].matrix=H;bpy.context.view_layer.update()
# Fold the little finger onto the near face, instead of pushing it through the opening.
for j,deg in [(1,65),(2,60),(3,35)]:
 b=r.pose.bones[f'pinky_{j:02}_l'];b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion((0,0,1),math.radians(deg))
bpy.context.view_layer.update()
f['grip_matrix']=[list(v) for v in NG];f['grip_in_root']=[list(v) for v in root.inverted()@NG];f['hand_in_root']=[list(v) for v in root.inverted()@H]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):f['basis'][b.name]=[list(v) for v in b.matrix_basis]
f['uniform_scale_from_previous']=.75
(O/'fit_final.json').write_text(json.dumps(f,indent=2));(O/'fit_pose.json').write_text(json.dumps(f,indent=2))
# Export code uses the original idle root to map geometry back to bind space.
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Foregrip_Fitted.blend'))
print('COMPACT_FIT_READY')
