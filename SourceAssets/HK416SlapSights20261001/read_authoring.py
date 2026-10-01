import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'HK416CommonAttachments20260930/HK416_Modular_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];ri=r.data.bones['WPN_root'].matrix_local.inverted();report={}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 if o.get('HK416_SourceObject') not in ('Buttons_low','ironsight_low') and not o.get('inspect_skin_source'):continue
 verts=[ri@o.matrix_world@v.co for v in o.data.vertices]
 groups={}
 for name in ('WPN_BoltCatch','hand_l'):
  if name not in o.vertex_groups:continue
  idx=o.vertex_groups[name].index;ids=[v.index for v in o.data.vertices if any(g.group==idx and g.weight>.7 for g in v.groups)]
  if ids:groups[name]={'count':len(ids),'min':[min(verts[i][k] for i in ids) for k in range(3)],'max':[max(verts[i][k] for i in ids) for k in range(3)]}
 report[o.name]={'source':o.get('HK416_SourceObject'),'verts':len(verts),'polygons':len(o.data.polygons),'materials':[m.name if m else None for m in o.data.materials],'groups':groups}
(O/'source_parts.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
