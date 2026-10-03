import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Draft.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
result={}
for f in (310,320,344):
    s.frame_set(f);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();root=r.pose.bones['WPN_root'].matrix.inverted()
    ob=bpy.data.objects['A762_Bolt'];ev=ob.evaluated_get(deps);mesh=ev.to_mesh();M=root@r.matrix_world.inverted()@ev.matrix_world
    vv=[M@v.co for v in mesh.vertices];faces=[list(p.vertices) for p in mesh.polygons];tree=BVHTree.FromPolygons(vv,faces)
    skin=bpy.data.objects['SK_Manny_Arms_Export'];se=skin.evaluated_get(deps);sm=se.to_mesh();MS=root@r.matrix_world.inverted()@se.matrix_world
    groups={g.index:g.name for g in skin.vertex_groups}
    rows={}
    for digit in ('index','middle','ring','pinky','thumb'):
        candidates=[]
        for v in skin.data.vertices:
            if sum(g.weight for g in v.groups if groups[g.group].startswith(digit) and groups[g.group].endswith('_r'))<.5:continue
            pt=MS@sm.vertices[v.index].co;hit=tree.find_nearest(pt)
            candidates.append((hit[3],list(pt),list(hit[0])))
        rows[digit]=min(candidates)
    result[f]=rows;print('CONTACT',f,{n:round(v[0]*1000,2) for n,v in rows.items()},flush=True)
    if f==310:
        result['bolt_vertices']=list(map(list,vv));result['bolt_faces']=faces
        indices=json.loads((O/'geometry.json').read_text())['skin']['indices']
        result['skin_vertices']=[list(MS@sm.vertices[i].co) for i in indices]
    ev.to_mesh_clear();se.to_mesh_clear()
(O/'contact_diagnosis.json').write_text(json.dumps(result),encoding='utf-8')
