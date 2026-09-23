"""Read current stock shells and shared stock interfaces for authoring only."""
import bpy, json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent; S=O.parent
O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST'
ob=bpy.data.objects['SM_SVD_Body'];X=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted()@ob.matrix_world
verts=[X@v.co for v in ob.data.vertices];neighbors=[set() for v in verts];coincident={}
for i,v in enumerate(verts):coincident.setdefault(tuple(round(x,5) for x in v),[]).append(i)
for same in coincident.values():
 for i in same[1:]:neighbors[same[0]].add(i);neighbors[i].add(same[0])
for e in ob.data.edges:a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
seen=set();islands=[]
for i in range(len(verts)):
 if i in seen:continue
 queue=[i];seen.add(i);ids=[]
 while queue:
  a=queue.pop();ids.append(a)
  for b in neighbors[a]-seen:seen.add(b);queue.append(b)
 lo=[min(verts[k][j] for k in ids) for j in range(3)];hi=[max(verts[k][j] for k in ids) for j in range(3)]
 slots=sorted({f.material_index for f in ob.data.polygons if f.vertices[0] in set(ids)})
 islands.append({'indices':ids,'min':lo,'max':hi,'slots':slots})
result={'body_object':ob.name,'materials':[m.name for m in ob.data.materials],
 'vertices':[list(v) for v in verts],'faces':[list(f.vertices) for f in ob.data.polygons],'islands':islands,'donors':{}}
print('SVD_BODY_MATERIALS',result['materials'],flush=True)
for i,row in enumerate(islands):
 if row['max'][1]>.025:print('SVD_REAR_SHELL',i,len(row['indices']),[round(v,4) for v in row['min']],[round(v,4) for v in row['max']],row['slots'],flush=True)
for n in ['WPN_root','hand_r','WPN_grip','WPN_stock']:
 b=r.data.bones.get(n)
 if b:print('SVD_BONE',n,list((r.data.bones['WPN_root'].matrix_local.inverted()@b.matrix_local).translation),flush=True)
sources=json.loads((S/'A762Meshy20260920/Accessories05/sources.json').read_text())
for key in ['skeleton','core_stock','qr_performance','tactical_telescopic']:
 info=sources['meshes'][key];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['source'][0])
 rows=[]
 for ob in [o for o in bpy.context.scene.objects if o.type=='MESH']:
  vs=[ob.matrix_world@v.co for v in ob.data.vertices]
  row={'name':ob.name,'vertices':len(vs),'min':[min(v[j] for v in vs) for j in range(3)],'max':[max(v[j] for v in vs) for j in range(3)],'slots':[m.name for m in ob.data.materials]};rows.append(row)
  print('STOCK_DONOR',key,row,flush=True)
 result['donors'][key]={'source':info,'objects':rows}
(O/'geometry_inputs.json').write_text(json.dumps(result,indent=2))
