import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'))
o=bpy.data.objects['SM_Warhammer_head_mount_factory'];v=[x.co for x in o.data.vertices]
def bounds(rows):return [[min(x[i] for x in rows),max(x[i] for x in rows)] for i in range(3)]
info={'object':o.name,'location':list(o.location),'scale':list(o.scale),'bounds':bounds(v),
      'middle_bounds':bounds([x for x in v if .89<x.z<.96]),'materials':[m.name for m in o.data.materials],
      'uv':[a.name for a in o.data.uv_layers]}
info['sections']={str(z):bounds([x for x in v if abs(x.z-z)<.002]) for z in (.865,.88,.90,.925,.95,.97,.99) if any(abs(x.z-z)<.002 for x in v)}
(P/'source_geometry.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print(json.dumps(info))
