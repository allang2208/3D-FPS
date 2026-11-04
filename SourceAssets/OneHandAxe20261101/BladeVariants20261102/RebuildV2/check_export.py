"""Requested model diagnosis: FBX roundtrip topology, normals, planes and stock mating end."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,kdtree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'ModulesV1/TacticalHatchet_Modules_Editable.blend'))
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory']
root=[v.co.copy() for v in factory.data.vertices if v.co.z<.11501]
tree=kdtree.KDTree(len(root))
for i,p in enumerate(root):tree.insert(p,i)
tree.balance();records=[]
for kind in ['SwiftCrescent','HeavyCleaver','FoldedArc']:
    entry=json.loads((P/(kind+'.json')).read_text('utf-8'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=entry['fbx'])
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    # FBX splits edges for author normals and UV; weld coordinates for topology diagnosis.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-7)
    bm.normal_update()
    lower=[obj.matrix_world@v.co for v in obj.data.vertices if (obj.matrix_world@v.co).z<.11501]
    errors=[tree.find(p)[2] for p in lower]
    item={'kind':kind,'imported_triangles':len(obj.data.polygons),'boundary_edges':sum(e.is_boundary for e in bm.edges),
          'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces),
          'stock_mating_vertices':len(lower),'max_mating_deviation_mm':max(errors)*1000,
          'finite_uvs':all(math.isfinite(c) for v in obj.data.uv_layers.active.data for c in v.uv),
          'finite_corner_normals':all(math.isfinite(c) for n in obj.data.corner_normals for c in n.vector)}
    bm.free()
    assert item['boundary_edges']==0 and item['nonmanifold_edges']==0 and item['degenerate_faces']==0,item
    assert item['finite_uvs'] and item['finite_corner_normals'] and item['max_mating_deviation_mm']<.02,item
    records.append(item)
(P/'export_diagnosis.json').write_text(json.dumps({'complete':True,'parts':records,'scope':'exported model only; no gameplay test'},indent=2)+'\n',encoding='utf-8')
print('EXPORTED_MODELS_DIAGNOSED '+json.dumps(records),flush=True)
