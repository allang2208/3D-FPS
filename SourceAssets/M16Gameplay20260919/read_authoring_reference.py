"""Read the existing authoring poses and contact anchors before adapting M16."""
import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT=Path(r'D:/FPS3D/FPSGAME/SourceAssets')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
idle=bpy.data.actions['M4_idle'];r.animation_data.action=idle;r.animation_data.action_slot=idle.slots[0];s.frame_set(0)
root=r.pose.bones['WPN_root'].matrix.copy();inv=root.inverted()
out={'fps':s.render.fps,'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},'bones':{},'parts':{}}
for b in r.pose.bones:
    if b.name.startswith('WPN') or b.name in ['hand_l','hand_r','index_01_r','middle_01_r','middle_01_l','thumb_01_l']:
        out['bones'][b.name]=list(inv@b.matrix.translation)
dg=bpy.context.evaluated_depsgraph_get()
for ob in s.objects:
    if ob.type!='MESH' or not ob.name.endswith('_Export') or ob.name=='SK_Manny_Arms_Export':continue
    ev=ob.evaluated_get(dg);m=ev.to_mesh();vs=[inv@r.matrix_world.inverted()@ev.matrix_world@v.co for v in m.vertices]
    out['parts'][ob.name]={'bounds':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],'groups':[g.name for g in ob.vertex_groups]}
    ev.to_mesh_clear()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'M16A2Migration20260919/M16A2_Mechanical_Editable.blend'),use_scripts=False)
out['m16_parts']={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    vs=[v.co for v in ob.data.vertices]
    out['m16_parts'][ob.name]={'bounds_cm':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)]}
(Path(__file__).parent/'authoring_reference.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
