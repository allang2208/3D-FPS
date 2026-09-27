"""Verify the six saved active UE meshes by reading their exported geometry."""
import bpy,bmesh,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
result={}
for path in sorted((ROOT/'UEAfter').glob('*.fbx')):
    bpy.ops.import_scene.fbx(filepath=str(path))
    obj=next(o for o in bpy.context.selected_objects if o.type=='MESH')
    bm=bmesh.new();bm.from_mesh(obj.data)
    # UE's exported render vertices may split at UV seams. These selected
    # meshes contain no coincident mating solids within a single material piece.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002)
    row={'boundary_edges':sum(e.is_boundary for e in bm.edges),
         'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
         'degenerate_faces':sum(f.calc_area()<1e-8 for f in bm.faces),
         'signed_volume_cm3':bm.calc_volume(signed=True)}
    bm.free()
    obj.data.calc_loop_triangles();uv=obj.data.uv_layers[0];bad=0
    for tri in obj.data.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<1e-11:bad+=1
    row['degenerate_uv_triangles']=bad
    result[path.stem]=row
    bpy.data.objects.remove(obj,do_unlink=True)
report={'meshes':result,'passed':len(result)==6 and all(r['boundary_edges']==0 and r['nonmanifold_edges']==0 and r['degenerate_faces']==0 and r['signed_volume_cm3']>0 and r['degenerate_uv_triangles']==0 for r in result.values())}
(ROOT/'ue_geometry_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
