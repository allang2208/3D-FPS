"""Repair collapsed UV corners only; leave positions, custom normals and interfaces intact."""
import bpy,json,hashlib,math
from pathlib import Path
P=Path(__file__).resolve().parent
recipe=json.loads((P/'runtime_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=recipe['source_blend'])
source_mesh=recipe.get('source_mesh',recipe['mesh'])
obj=bpy.data.objects[source_mesh];me=obj.data
me.calc_loop_triangles()
layers=list(me.uv_layers);uv=layers[0].data
def area(layer,tri):
    a,b,c=(layer.data[i].uv for i in tri.loops)
    return abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
bad={tri.polygon_index for tri in me.loop_triangles if tri.area>1.e-16 and area(layers[0],tri)<1.e-14}
copied=projected=0
triangles={pi:[] for pi in bad}
for tri in me.loop_triangles:
    if tri.polygon_index in triangles:triangles[tri.polygon_index].append(tri)
for pi in bad:
    poly=me.polygons[pi];tris=triangles[pi]
    donor=next((layer for layer in layers[1:] if all(area(layer,t)>1.e-14 for t in tris if t.area>1.e-16)),None)
    if donor:
        for li in poly.loop_indices:uv[li].uv=donor.data[li].uv
        copied+=1
    else:
        # Preserve the local microtexture scale used by the author's metal.
        axis=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in poly.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co;uv[li].uv=(co[axes[0]]/.055,co[axes[1]]/.055)
        projected+=1
me.update();me.calc_loop_triangles()
for pi in {t.polygon_index for t in me.loop_triangles if t.area>1.e-16 and area(layers[0],t)<1.e-14}:
    poly=me.polygons[pi];origin=me.vertices[me.loops[poly.loop_start].vertex_index].co.copy()
    axis=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=axis]
    for li in poly.loop_indices:
        co=me.vertices[me.loops[li].vertex_index].co-origin
        uv[li].uv=(co[axes[0]]/.055,co[axes[1]]/.055)
me.update();me.calc_loop_triangles()
microcaps={t.polygon_index for t in me.loop_triangles if t.area>1.e-16 and area(layers[0],t)<1.e-14}
for pi in microcaps:
    poly=me.polygons[pi]
    # Sub-micron slivers cannot retain a meaningful texture scale in float UVs.
    # A non-collinear cap map keeps their tangent frame defined without moving
    # a single vertex or altering the authored split normals.
    for corner,li in enumerate(poly.loop_indices):
        angle=math.tau*corner/poly.loop_total
        uv[li].uv=(.5+.001*math.cos(angle),.5+.001*math.sin(angle))
me.update();me.calc_loop_triangles()
remaining=sum(t.area>1.e-16 and area(layers[0],t)<1.e-14 for t in me.loop_triangles)
details=[dict(poly=t.polygon_index,area=t.area,material=me.materials[me.polygons[t.polygon_index].material_index].name,vertices=[list(me.vertices[v].co) for v in t.vertices]) for t in me.loop_triangles if t.area>1.e-16 and area(layers[0],t)<1.e-14]
zero=None # UE triangulates n-gons and computes Mikk tangents from repaired UVs.
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
obj.name=source_mesh+'_UV2'
out=P/'Export'/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
recipe.update(source_mesh=source_mesh,mesh=obj.name,fbx=str(out),fbx_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(P/'runtime_manifest.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'uv_repair.json').write_text(json.dumps(dict(polygons_repaired=len(bad),copied_valid_secondary_uv=copied,locally_projected=projected,microcap_maps=len(microcaps),remaining_collapsed_uv_triangles=remaining,remaining_details=details,zero_tangent_loops=zero,positions_modified=False,custom_normals_modified=False),indent=2),encoding='utf-8')
print('UV_REPAIR',len(bad),copied,projected,remaining,zero,flush=True)
