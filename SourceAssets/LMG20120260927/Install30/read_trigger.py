import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refine29/LMG201_R29_Editable.blend'),use_scripts=False)
ob=bpy.data.objects['TriggerGuardAssembly'];me=ob.data
parent=list(range(len(me.vertices)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for e in me.edges:
 a,b=[find(v) for v in e.vertices];parent[a]=b
parts={}
for v in me.vertices:parts.setdefault(find(v.index),[]).append(ob.matrix_world@v.co)
print(json.dumps([{'count':len(ps),'bounds':[[min(p[k] for p in ps),max(p[k] for p in ps)] for k in range(3)]} for ps in sorted(parts.values(),key=len,reverse=True)[:12]]),flush=True)
