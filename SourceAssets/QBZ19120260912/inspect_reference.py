import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions.get('M4_MAT_idle') or bpy.data.actions.get('M4_HK416_idle') or bpy.data.actions.get('M4_idle')
print('ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions]);print('SELECTED',a)
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();inv=(r.matrix_world@root).inverted();dg=bpy.context.evaluated_depsgraph_get()
rep={'actions':[(a.name,list(a.frame_range)) for a in bpy.data.actions], 'bones':{b.name:list((root.inverted()@b.matrix).translation) for b in r.pose.bones if b.name.startswith('WPN_') or b.name in ['hand_l','hand_r','index_01_r','middle_01_r','middle_01_l']},'meshes':[]}
for o in s.objects:
 if o.type!='MESH':continue
 e=o.evaluated_get(dg);m=e.to_mesh();pts=[inv@o.matrix_world@v.co for v in m.vertices]
 rep['meshes'].append({'name':o.name,'vertices':len(pts),'min':[min(v[j] for v in pts) for j in range(3)],'max':[max(v[j] for v in pts) for j in range(3)]});e.to_mesh_clear()
(O/'reference.json').write_text(json.dumps(rep,indent=2))
print(json.dumps(rep['bones']))
