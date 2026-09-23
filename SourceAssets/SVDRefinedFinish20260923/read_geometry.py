import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'SVDStockAdapter20260923'
bpy.ops.wm.open_mainfile(filepath=str(S/'SVD_StockModular_Editable.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
rig.data.pose_position='REST'
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
report={'rig':rig.name,'root': [list(r) for r in root], 'objects':{}}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or 'Scope' not in ob.name:continue
 points=[root.inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
 adj=[set() for _ in points]
 for e in ob.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 unseen=set(range(len(points)));islands=[]
 while unseen:
  seed=unseen.pop();group=[seed];todo=[seed]
  while todo:
   for n in adj[todo.pop()]:
    if n in unseen:unseen.remove(n);group.append(n);todo.append(n)
  lo=[min(points[i][k] for i in group) for k in range(3)];hi=[max(points[i][k] for i in group) for k in range(3)]
  islands.append({'verts':len(group),'min':lo,'max':hi})
 row={'vertices':len(points),'materials':[m.name for m in ob.data.materials], 'islands':sorted(islands,key=lambda x:-x['verts'])}
 report['objects'][ob.name]=row
 print(ob.name,len(points),len(islands),row['materials'],json.dumps(row['islands'][:12]),flush=True)
(O/'geometry_inputs.json').write_text(json.dumps(report,indent=2))
print('SVD_GEOMETRY_INPUTS_READY',flush=True)
