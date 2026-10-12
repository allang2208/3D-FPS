"""Rebuild only Super90's editable skin from the exact native UE surface."""
import gzip,json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
O=Path(__file__).parent
def apply_to_blender(arms,rig):
 d=json.loads(gzip.decompress((O/'arms_before.json.gz').read_bytes()))
 patch=json.loads((O/'patches.json').read_text())['arms']
 # This hook belongs to this Super90 native bind, not the shared M4 master.
 for name,bone in d['bones'].items():
  if name not in rig.data.bones:continue
  actual=rig.matrix_world@rig.data.bones[name].matrix_local.translation
  expected=Vector((bone['position'][0]/100,-bone['position'][1]/100,bone['position'][2]/100))
  if (actual-expected).length>1e-5:raise RuntimeError('Super90 native bind changed: '+name)
 positions=list(d['positions'])
 for vi,p in patch['positions']:positions[vi]=p
 normal_patch={vi:n for vi,n in patch['normals']}
 materials=[slot.material for slot in arms[0].material_slots]
 assert len(materials)==3
 me=bpy.data.meshes.new('Super90_ContinuousSkin_20261012')
 me.from_pydata([(p[0]/100,-p[1]/100,p[2]/100) for p in positions],[],d['triangles']);me.update()
 ob=bpy.data.objects.new('Super90_V7_ContinuousSkin',me);bpy.context.scene.collection.objects.link(ob)
 for m in materials:me.materials.append(m)
 for i,f in enumerate(me.polygons):f.use_smooth=True;f.material_index=d['materials'][i]
 for channel in range(4):
  layer=me.uv_layers.new(name=('UVMap' if channel==0 else 'Canonical'+str(channel)))
  for ti,face in enumerate(me.polygons):
   for li,corner in zip(face.loop_indices,(0,1,2)):
    a,b=d['uv'][channel][ti][corner];layer.data[li].uv=(a,1-b)
 loop_normals=[]
 for ti,face in enumerate(d['triangles']):
  for corner in (0,1,2):
   n=normal_patch.get(face[corner],d['normals'][ti][corner]);loop_normals.append((n[0],-n[1],n[2]))
 me.normals_split_custom_set(loop_normals)
 for name in sorted({n for row in d['weights'] for n in row}):ob.vertex_groups.new(name=name)
 for vi,row in enumerate(d['weights']):
  for name,weight in row.items():ob.vertex_groups[name].add([vi],weight,'REPLACE')
 ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 ob.modifiers.new('Native V7 Binding','ARMATURE').object=rig
 for old in arms:bpy.data.objects.remove(old,do_unlink=True)
 ob.name='Super90_V7_ContinuousSkin'
 ob['surface_revision']='20261012: exact native weights, local surface fairing'
 return [ob]
