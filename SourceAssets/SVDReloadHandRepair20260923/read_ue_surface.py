"""Compare the imported skin with the source pose in the same local coordinates."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'UE_Readback.blend'))
r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SK_SVD_ModularStock.001']
src=json.loads((O/'source_before.json').read_text())
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
p={n:Matrix(m) for n,m in src['poses']['220'].items()}
for n,m in p.items():r.pose.bones[n].matrix_basis=lr[n].inverted()@(p[parent[n]].inverted()@m if parent[n] else m)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);m=ev.to_mesh()
inv=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted();X=inv@ev.matrix_world
groups={g.index:g.name for g in ob.vertex_groups}
parts=[]
for label,hand,color in [('ImportedLeftHand',True,(.48,.31,.18,1)),('ImportedMagazine',False,(.22,.25,.29,1))]:
 used=[]
 for v in ob.data.vertices:
  w=sum(g.weight for g in v.groups if ((groups[g.group].endswith('_l') and groups[g.group].startswith(('hand','thumb','index','middle','ring','pinky'))) if hand else groups[g.group]=='WPN_mag'))
  if w>.9:used.append(v.index)
 mp={v:i for i,v in enumerate(used)}
 vs=[list(X@m.vertices[i].co) for i in used];fs=[[mp[i] for i in f.vertices] for f in m.polygons if all(i in mp for i in f.vertices)]
 parts.append({'name':label,'vertices':vs,'faces':fs,'color':color})
ev.to_mesh_clear()
(O/'ue_hand_surface.json').write_text(json.dumps({'parts':parts}))
print('SVD_UE_SKIN_SURFACE',[(p['name'],len(p['vertices'])) for p in parts])
