import bpy,bmesh,json,hashlib
from pathlib import Path
O=Path(__file__).parent;report={}
for path in O.glob('SM_AKM_Mount_*.fbx'):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bm=bmesh.new();bm.from_mesh(o.data)
 result={'triangles':sum(len(f.verts)-2 for f in bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'uv_layers':len(o.data.uv_layers),'fbx_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 assert result['nonmanifold_edges']==0 and result['degenerate_faces']==0 and result['uv_layers']>0,result
 report[path.name]=result;bm.free()
(O/'geometry.json').write_text(json.dumps(report,indent=2));print('BRIDGE_GEOMETRY_PASS')
