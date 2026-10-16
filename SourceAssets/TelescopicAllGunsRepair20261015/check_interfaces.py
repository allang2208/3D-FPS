import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'inputs.json').read_text());X=O/'Working'
R={}
for key,row in D['assets'].items():
 R[key]={};names={row['slots'][i]['material'].split('.')[-1] for i in range(len(row['slots'])) if i not in D['body_slots'][key]}
 for tag,path in [('before',row['export']),('after',str(O/'Exports'/(key+'.fbx')))]:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=path);points=[];faces=0
  for ob in bpy.context.scene.objects:
   if ob.type!='MESH':continue
   me=ob.data;mids={i for i,m in enumerate(me.materials) if m and any(m.name==n or m.name.startswith(n+'.') for n in names)}
   polys=[f for f in me.polygons if f.material_index in mids];faces+=len(polys);ids={i for f in polys for i in f.vertices};points.extend(tuple(ob.matrix_world@me.vertices[i].co) for i in ids)
  np.save(X/(key+'_interface_'+tag+'.npy'),np.asarray(points));R[key][tag]={'triangles':faces,'vertices':len(points)}
(O/'interface_counts.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
