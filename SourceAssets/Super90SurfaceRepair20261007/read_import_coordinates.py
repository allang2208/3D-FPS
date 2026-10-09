import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
me=bpy.data.objects['Super90_body'].data;me.calc_loop_triangles();me.calc_tangents(uvmap=me.uv_layers[0].name)
rows={tuple(sorted(tuple(round(x,3) for x in me.vertices[v].co) for v in tri.vertices)):tri for tri in me.loop_triangles}
out=[]
for tri in json.loads((O/'ue_surface_inputs.json').read_text())['render']:
    key=tuple(sorted((round(p[0]/100,3),round(-p[1]/100,3),round(p[2]/100,3)) for p in tri['position']))
    src=rows.get(key)
    if not src:continue
    data=[]
    for p,uv,n,t,b in zip(tri['position'],tri['uv'],tri['normal'],tri['tangent'],tri['bitangent']):
        pt=Vector((p[0]/100,-p[1]/100,p[2]/100));i=min(src.loops,key=lambda i:(me.vertices[me.loops[i].vertex_index].co-pt).length)
        sv=me.uv_layers[0].data[i].uv;sn=me.corner_normals[i].vector
        st=me.loops[i].tangent;sb=sn.cross(st)*me.loops[i].bitangent_sign
        data.append({'uv_ue':uv,'uv_expected':[sv.x,1-sv.y],'normal_ue':n,'normal_expected':[sn.x,-sn.y,sn.z],
        'tangent_dot':Vector(t).dot(Vector((st.x,-st.y,st.z))), 'bitangent_dot':Vector(b).dot(Vector((-sb.x,sb.y,-sb.z)))})
    out.append({'id':tri['id'],'corners':data})
(O/'coordinate_inputs.json').write_text(json.dumps(out,indent=2))
print('UV max delta',max(abs(c['uv_ue'][k]-c['uv_expected'][k]) for r in out for c in r['corners'] for k in range(2)))
print('Normal max delta',max(abs(c['normal_ue'][k]-c['normal_expected'][k]) for r in out for c in r['corners'] for k in range(3)))
print('Tangent min dot',min(c['tangent_dot'] for r in out for c in r['corners']))
print('Bitangent min dot',min(c['bitangent_dot'] for r in out for c in r['corners']))
print(json.dumps(out[:2]))
