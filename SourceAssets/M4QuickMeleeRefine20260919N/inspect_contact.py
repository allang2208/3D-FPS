import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'M4QuickMeleeRefine20260919K/Base/M4_QuickCombat_Base_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima']; bpy.context.scene.frame_set(0); bpy.context.view_layer.update()
w=rig.pose.bones['WPN_root'].matrix; ti=w.inverted() @ rig.matrix_world.inverted()
ob=next(o for o in bpy.data.objects if o.type=='MESH' and o.name=='M4_Grip Default Unreal_Export')
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
verts=[ti @ ev.matrix_world @ v.co for v in me.vertices]
me.clear_geometry();ev.to_mesh_clear()
out={'grip_vertices_gun_local':[list(v) for v in verts], 'bone_positions_gun_local':{b.name:list((w.inverted() @ b.matrix).translation) for b in rig.pose.bones if b.name=='hand_r' or (b.name.endswith('_r') and any(s in b.name for s in ('thumb','index','middle','ring','pinky')))}}
(P/'grip_geometry.json').write_text(json.dumps(out))
print('GRIP_BOUNDS',[(min(v[i] for v in verts),max(v[i] for v in verts)) for i in range(3)],flush=True)
print('HAND_POINTS',out['bone_positions_gun_local'],flush=True)
