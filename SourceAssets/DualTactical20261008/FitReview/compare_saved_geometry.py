"""Ensure every saved UE surface is the same fitted surface reviewed offline."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;m=json.loads((O/'Repaired/manifest.json').read_text());saved=json.loads((O/'saved-readback.json').read_text());report={}
for key,e in m.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'Repaired'/(key+'.blend')))
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    authored=[v.co.copy() for v in body.data.vertices];faces=[list(p.vertices) for p in body.data.polygons];expected=BVHTree.FromPolygons(authored,faces)
    used={i for f in faces for i in f};bearing={i for p in body.data.polygons if body.data.materials[p.material_index].name.startswith('Tactical_Fitted_Bearing') for i in p.vertices}
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=saved[key]['fbx'])
    vertices=[];polygons=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        base=len(vertices);transform=Matrix(e['canonical'])@ob.matrix_world
        vertices.extend([transform@v.co for v in ob.data.vertices]);polygons.extend([[base+i for i in p.vertices] for p in ob.data.polygons])
    actual=BVHTree.FromPolygons(vertices,polygons)
    imported_error=max(expected.find_nearest(p)[3]*1000 for p in vertices)
    source_errors={i:actual.find_nearest(authored[i])[3]*1000 for i in used}
    worst=max(imported_error,max(source_errors.values()))
    report[key]={'maximum_surface_difference_mm':worst,'saved_to_source_mm':imported_error,'bearing_maximum_difference_mm':max(source_errors[i] for i in bearing),'worst_source_vertices':[[list(authored[i]),source_errors[i]] for i in sorted(source_errors,key=source_errors.get,reverse=True)[:3]],'saved_triangles':len(polygons),'passed':worst<.025}
    print('SAVED_SURFACE',key,round(worst,6),flush=True)
(O/'After/saved-geometry-report.json').write_text(json.dumps(report,indent=2))
if any(not e['passed'] for e in report.values()):raise RuntimeError('Saved geometry differs from reviewed fit')
