import bpy,json
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/M4_Assembled_Candidate.blend')
for name in ['M4 Body','Handguard Kmode Unreal']:
 o=bpy.data.objects[name];adj=[[]for v in o.data.vertices]
 for e in o.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
 seen=set()
 for i in range(len(adj)):
  if i in seen:continue
  todo=[i];seen.add(i);ids=[]
  while todo:
   v=todo.pop();ids.append(v)
   for n in adj[v]:
    if n not in seen:seen.add(n);todo.append(n)
  pts=[o.matrix_world@o.data.vertices[v].co for v in ids];bounds=[[min(v[j]for v in pts),max(v[j]for v in pts)]for j in range(3)]
  if bounds[2][1]>.09:print(name,len(ids),bounds)
