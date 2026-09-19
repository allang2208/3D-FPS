import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'))
o=bpy.data.objects['AK'];me=o.data
adj=[[] for v in me.vertices]
for e in me.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();groups=[]
for v in me.vertices:
 if v.index in seen:continue
 stack=[v.index];seen.add(v.index);ids=[]
 while stack:
  k=stack.pop();ids.append(k)
  for j in adj[k]:
   if j not in seen:seen.add(j);stack.append(j)
 pts=[o.matrix_world@me.vertices[i].co for i in ids]
 groups.append({'ids':ids,'n':len(ids),'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
groups.sort(key=lambda g:-g['n']);(O/'components.json').write_text(json.dumps(groups,indent=2))
print('COMPONENTS',json.dumps([{k:v for k,v in g.items() if k!='ids'} for g in groups]))
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AKMIntegration20260910/EquipCharge/AKM_EquipCharge_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];inv=r.data.bones['WPN_root'].matrix_local.inverted();a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
out={}
for o in bpy.context.scene.objects:
 if o.type=='MESH' and o.name.startswith('AKMR'):
  pts=[inv@r.matrix_world.inverted()@o.matrix_world@v.co for v in o.data.vertices];out[o.name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)],'groups':[g.name for g in o.vertex_groups]}
out['bones']={b.name:list((inv@b.matrix_local).translation) for b in r.data.bones if b.name.startswith('WPN')}
(O/'old_bounds.json').write_text(json.dumps(out,indent=2));print('OLD',json.dumps(out))
