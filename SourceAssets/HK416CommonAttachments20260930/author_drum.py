"""Keep the accepted drum/contact; fit the original HK feed tower above it."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;H=O.parent/'HK416Reworked20260930';R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix'])
bpy.ops.wm.read_factory_settings(use_empty=True)
def part(file,name,cut,keep_upper):
 with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
 ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.transform(R.inverted())
 bm=bmesh.new();bm.from_mesh(ob.data)
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=keep_upper,clear_outer=not keep_upper,dist=1e-7)
 edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-6 for v in e.verts)]
 if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.transform(R);return ob
drum=part(O/'Meshes/SM_HK416_large_drum.blend','SM_HK416_large_drum',.001,False)
throat=part(H/'Exports/Attachments/SM_HK416_factory_magazine_Editable.blend','SM_HK416_factory_magazine',-.003,True)
# A real closed collar overlaps both capped solids. Keep the hollow original
# feed opening and upper latch exactly as authored on the HK factory magazine.
bpy.ops.mesh.primitive_cube_add(size=1,location=(-.000038,-.1197,-.001));collar=bpy.context.object;collar.scale=(.027,.071,.006)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bevel=collar.modifiers.new('Feed collar rounded edges','BEVEL');bevel.width=.0015;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
metal=bpy.data.materials.new('HK416_InterfaceSteel');collar.data.materials.append(metal);collar.data.transform(R@collar.matrix_world);collar.matrix_world=Matrix.Identity(4)
obs=[drum,throat,collar]
for o in obs:
 coords=[[tuple(d.uv) for d in layer.data] for layer in list(o.data.uv_layers)[:3]]
 for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
 for i in range(4):
  uv=o.data.uv_layers.new(name='HK416_UV'+str(i))
  if i<len(coords):
   for j,p in enumerate(coords[i]):uv.data[j].uv=p
 for f in o.data.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[i for i in range(3) if i!=axis]
  for li in f.loop_indices:
   p=o.data.vertices[o.data.loops[li].vertex_index].co;o.data.uv_layers[3].data[li].uv=(p[a]/.04,p[b]/.04)
bpy.ops.object.select_all(action='DESELECT')
for ob in obs:ob.select_set(True);ob.hide_set(False)
bpy.context.view_layer.objects.active=drum;bpy.ops.object.join();drum.name='SM_HK416_large_drum'
file=O/'Meshes/SM_HK416_large_drum.fbx';bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
bpy.data.libraries.write(str(file.with_suffix('.blend')),{drum},fake_user=True)
report=json.loads((O/'models.json').read_text());bindings=report['parts']['large_drum']['bindings']
bindings['M_HK416_Mag_Silencer_Magazine']='/Game/Weapons/HK416/Reworked20260930/Materials/M_HK416_Mag_Silencer_Magazine'
report['parts']['large_drum']['fit']='Original HK feed tower above -3mm, accepted donor drum below +1mm, closed beveled 6mm collar; held drum body unchanged'
(O/'models.json').write_text(json.dumps(report,indent=2));print('HK416_FACTORY_FEED_DRUM_SAVED',flush=True)
