"""Measure the reported 201 drum joint in its actual magazine attachment frame."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;D=O.parent/'Drum46';cap=json.loads((O/'capture.json').read_text());g=json.loads((D/'geometry_inputs.json').read_text());root_from_mag=Matrix(g['root_blender']).inverted()@Matrix(g['mag_blender'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/CurrentDrum.fbx'),use_anim=False)
obj=next(a for a in bpy.data.objects if a.type=='MESH');out={};obj.data.transform(root_from_mag@obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
for mi,slot in enumerate(cap['assets']['Drum']['slots']):
 ids={i for f in obj.data.polygons if f.material_index==mi for i in f.vertices};points=np.array([tuple(obj.data.vertices[i].co) for i in ids])
 if not len(points):continue
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=mi],context='FACES');boundary=[e for e in bm.edges if e.is_boundary];leaks=[e for e in boundary if e.calc_length()>.0002]
 out[slot['name']]={'bounds_root_m':[points.min(0).tolist(),points.max(0).tolist()],'verts':len(points),'faces':sum(f.material_index==mi for f in obj.data.polygons),'open_edges':len(boundary),'open_edges_over_0_2mm':len(leaks),'longest_boundary_mm':1000*max((e.calc_length() for e in boundary),default=0)}
 bm.free()
(O/'joint_before.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
