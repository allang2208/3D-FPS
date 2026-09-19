import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SourceMatched/AKM_Fab_SourceMatched_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima']
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('AKMR_'):continue
 wood=[p for p in o.data.polygons if o.data.materials[p.material_index].name=='M_AKMR_Walnut']
 if not wood:continue
 ids=set(v for p in wood for v in p.vertices)
 xyz=np.array([list(o.data.vertices[v].co) for v in ids]);mean=xyz.mean(axis=0);w,axes=np.linalg.eigh(np.cov(xyz.T))
 print('WOOD_INFO',o.name,'faces',len(wood),'bounds',xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist(),'axes',axes.tolist())
 print('ROOT', [list(x) for x in r.data.bones['WPN_root'].matrix_local])
