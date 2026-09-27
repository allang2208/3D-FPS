"""Read the accepted M1911 attachment surfaces for fitting; no render/test."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
source=O.parent/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST'
bpy.context.view_layer.update();root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
record={'source':str(source),'root_matrix':[list(r) for r in root],'parts':{}}
for ob in bpy.data.collections['M1911_LOW'].objects:
    if ob.name in ['M1911_LeftWoodPanel','M1911_RightWoodPanel','M1911_Frame'] or ob.name.startswith('M1911_GripScrew_'):
        xf=root.inverted()@ob.matrix_world
        pts=[xf@v.co for v in ob.data.vertices]
        record['parts'][ob.name]={'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],
            'bone':ob.get('bone'),'triangles':len(ob.data.polygons)}
(O/'source_geometry.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('PISTOL_GRIP_SURFACE_INPUT '+json.dumps(record),flush=True)
