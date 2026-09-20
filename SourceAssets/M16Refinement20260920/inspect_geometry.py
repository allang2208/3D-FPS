import bpy,json,bmesh,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;I=json.loads((O/'blender_inspection.json').read_text());out={}
bpy.ops.wm.open_mainfile(filepath=str(S/'M16UniversalAttachments20260920/M16_CommonAttachments_Editable.blend'),use_scripts=False)
for key in ['holographic','balanced_reargrip','panoramic_red_dot','lpvo_1_6x','prism_scope_2x']:
 o=bpy.data.objects['SM_M16_'+key];mesh=o.data;mesh.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4);components=[];left=set(range(len(mesh.vertices)));adj={v.index:set() for v in mesh.vertices}
 for e in mesh.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 while left:
  todo=[left.pop()];indices=set(todo)
  while todo:
   for n in adj[todo.pop()]&left:left.remove(n);indices.add(n);todo.append(n)
  pts=[mesh.vertices[i].co for i in indices];faces=[p for p in mesh.polygons if p.vertices[0] in indices]
  components.append({'indices':sorted(indices),'count':len(indices),'faces':len(faces),'materials':list({mesh.materials[p.material_index].name for p in faces}),'bounds':[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]})
 out[key]=components
# Carry-handle channel: mesh ray samples at longitudinal stations.
from mathutils.bvhtree import BVHTree
part=I['parts']['M16A2_Receiver'];tree=BVHTree.FromPolygons([Vector(v) for v in part['vertices']],part['faces'])
out['channel']={}
for y in [-.19,-.17,-.15,-.13,-.11,-.09,-.07,-.05,-.03]:
 row=[]
 for x in [-.012,-.009,-.006,-.003,0,.003,.006,.009,.012]:
  hit=tree.ray_cast(Vector((x,y,.21)),Vector((0,0,-1)),.08)[0];row.append([x,hit.z if hit else None])
 out['channel'][str(y)]=row
(O/'geometry_inspection.json').write_text(json.dumps(out,indent=2));print('GEOMETRY_INSPECTED',flush=True)
