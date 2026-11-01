import bpy,json
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
result={}
for name in ('M24_MainScope_Lowpoly','M24_ExtraScope_Lowpoly','M24_ScopeGlass_Lowpoly','M24_TopGlass_Lowpoly'):
    ob=bpy.data.objects[name];points=[ob.matrix_world@v.co for v in ob.data.vertices]
    result[name]={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)],'center':[sum(v[i] for v in points)/len(points) for i in range(3)]}
(O/'top_geometry.json').write_text(json.dumps(result,indent=2));print('M24_DUAL_OPTIC_GEOMETRY',json.dumps(result),flush=True)
