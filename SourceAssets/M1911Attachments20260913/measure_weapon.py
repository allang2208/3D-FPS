"""Read the accepted gun's construction coordinates for accessory interfaces."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error) or 'SK_M1911_Manny' not in bpy.data.objects:raise
r=bpy.data.objects['SK_M1911_Manny'];r.data.pose_position='REST';bpy.context.view_layer.update()
root=r.matrix_world@r.data.bones['WPN_root'].matrix_local;inv=root.inverted()
def bounds(points):return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
parts={}
for ob in bpy.data.collections['M1911_LOW'].objects:
    if ob.type!='MESH':continue
    points=[inv@ob.matrix_world@v.co for v in ob.data.vertices]
    parts[ob.name]={'bone':ob.get('bone',''),'bounds':bounds(points)}
bones={b.name:{'parent':b.parent.name if b.parent else None,'gun_local':[list(row) for row in inv@r.matrix_world@b.matrix_local]} for b in r.data.bones if b.name.startswith('WPN')}
(O/'weapon_interfaces.json').write_text(json.dumps({'units':'metres in authored WPN_root frame','parts':parts,'bones':bones},indent=2))
print('M1911_INTERFACES_READY',flush=True)
