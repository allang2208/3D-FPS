import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
report={}
for key,path in [('m4',P.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'),('akm',P.parent/'AKMAttachments20260911/AKM_Attachments_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
 r=bpy.data.objects.get('SK_M4_Infima');assert r
 act=bpy.data.actions.get('AKM_Native_idle' if key=='akm' else 'M4_idle')
 if act:r.animation_data.action=act;r.animation_data.action_slot=act.slots[0]
 s.frame_set(0);bpy.context.view_layer.update();root=r.matrix_world@r.pose.bones['WPN_root'].matrix
 records=[]
 for o in s.objects:
  if o.type!='MESH' or not (o.name.endswith('_Export') or o.name=='AKM_Soviet_Native'):continue
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());pts=[root.inverted()@ev.matrix_world@v.co for v in ev.data.vertices]
  records.append({'name':o.name,'verts':len(pts),'hide':o.hide_render,'materials':[m.name if m else None for m in o.data.materials], 'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
  if key=='akm' and o.name=='AKM_Soviet_Native':
   adj=[[] for _ in pts]
   for e in o.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
   seen=set();groups=[]
   for v in range(len(pts)):
    if v in seen:continue
    todo=[v];seen.add(v);ids=[]
    while todo:
     n=todo.pop();ids.append(n)
     for j in adj[n]:
      if j not in seen:seen.add(j);todo.append(j)
    groups.append({'index':len(groups),'verts':len(ids),'min':[min(pts[j][i] for j in ids) for i in range(3)],'max':[max(pts[j][i] for j in ids) for i in range(3)]})
   report['akm_components']=groups
 report[key]={'source':str(path),'objects':records,'root_world':[list(row) for row in root],'root_rest':[list(row) for row in r.data.bones['WPN_root'].matrix_local]}
(P/'source_inspection.json').write_text(json.dumps(report,indent=2))
print('STOCK_SOURCES_INSPECTED')
