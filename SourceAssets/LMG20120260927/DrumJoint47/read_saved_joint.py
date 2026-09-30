"""Finish the user's specific open-joint diagnosis on the saved UE export."""
import bpy,bmesh,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/After_Drum.fbx'),use_anim=False)
a=next(o for o in bpy.data.objects if o.type=='MESH');bm=bmesh.new();bm.from_mesh(a.data)
# The three new adapter materials form one closed physical part. Material
# borders alone are not holes, so examine the complete adapter together.
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index<3],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
out={'scope':'User-reported open adapter only, saved UE export','boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'triangles':len(bm.faces),'runtime_tested':False,'rendered':False};bm.free();(O/'saved_joint_geometry.json').write_text(json.dumps(out,indent=2));print('D47_SAVED_JOINT',json.dumps(out),flush=True)
