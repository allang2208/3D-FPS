import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];root=r.data.bones['WPN_root'].matrix_local
body=bpy.data.objects['M24_base'];pts=[body.matrix_world@v.co for v in body.data.vertices]
report={'root':[list(v) for v in root],'sections':{}}
for y in (.3,.35,.4,.45,.5,.55,.6,.7,.8):
 p=[v for v in pts if abs(v.y-y)<.015]
 if p:report['sections'][str(y)]={'min':[min(v[i] for v in p) for i in range(3)],'max':[max(v[i] for v in p) for i in range(3)]}
report['objects']=[o.name for o in bpy.data.objects if o.type=='MESH' and 'M24' in o.name]
(O/'source_geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
