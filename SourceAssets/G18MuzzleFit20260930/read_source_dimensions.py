"""Read interface dimensions needed to author the four G18 muzzle variants."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent;R={}
def bounds(points):return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
bpy.ops.wm.open_mainfile(filepath=str(S/'G18Integration20260929/Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];inv=r.data.bones['WPN_root'].matrix_local.inverted();ob=bpy.data.objects['G18_G18']
mark=inv@r.data.bones['WPN_SOCKET_Muzzle'].head_local;group=ob.vertex_groups['WPN_Barrel'].index
v=[inv@p.co for p in ob.data.vertices if any(g.group==group and g.weight>.5 for g in p.groups)]
R['gun']={'muzzle_marker_root_m':list(mark),'barrel':bounds(v),'front_vertices_root_m':sorted({tuple(round(x,8) for x in p) for p in v if p.y<-.128})}
for key in ('suppressor','tactical_suppressor','brake','titanium_brake'):
    file=S/('M4Muzzles20260910/titanium_brake-editable.blend' if key=='titanium_brake' else f'G18Integration20260929/Attachments/SM_G18_{key}_Editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(file));ob=bpy.data.objects['SM_M4_titanium_brake' if key=='titanium_brake' else 'SM_G18_'+key]
    parts={}
    for face in ob.data.polygons:parts.setdefault(ob.data.materials[face.material_index].name,[]).extend(ob.matrix_world@ob.data.vertices[i].co for i in face.vertices)
    R[key]={'source':str(file),'matrix_world':[list(row) for row in ob.matrix_world],'parts':{name:bounds(p) for name,p in parts.items()},'sockets':{c.name:list(c.matrix_world.translation) for c in ob.children if c.type=='EMPTY'}}
(O/'source_dimensions.json').write_text(json.dumps(R,indent=2))
print('G18_MUZZLE_SOURCE_DIMENSIONS_WRITTEN')
