import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'HK416UniversalParts20260930';a=json.loads((S/'authoring.json').read_text());result={}
for family in ('Common','HK416'):
 entry=a[family+'/eoth_holographic'];bpy.ops.wm.open_mainfile(filepath=str(Path(entry['fbx']).with_name(entry['name']+'_Editable.blend')))
 ob=bpy.data.objects[entry['name']];row={'sockets':entry['sockets_blender_m'],'regions':{}}
 for i,m in enumerate(ob.data.materials):
  if not any(k in m.name for k in ('Reticle','Glass')):continue
  faces=[p for p in ob.data.polygons if p.material_index==i];ids={j for p in faces for j in p.vertices};points=[ob.data.vertices[j].co for j in ids]
  if not points:continue
  uvs=[ob.data.uv_layers[0].data[j].uv for p in faces for j in p.loop_indices]
  row['regions'][m.name]={'faces':len(faces),'verts':len(ids),'bounds':[[min(v[k] for v in points),max(v[k] for v in points)] for k in range(3)],'uv':[[min(v[k] for v in uvs),max(v[k] for v in uvs)] for k in range(2)],'normal':list(faces[0].normal)}
 result[family]=row
(O/'geometry_inputs.json').write_text(json.dumps(result,indent=2));print('EOTH_RETICLE_GEOMETRY_INPUTS_READ')
