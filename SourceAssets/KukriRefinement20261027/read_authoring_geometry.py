import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'KukriComponentVariants20261026/Kukri_Components_Editable.blend'))
result=[]
for name in ['SM_Kukri_LanyardBraid','SM_Kukri_LanyardTassel','SM_Kukri_LanyardTag','SM_Kukri_PommelSteel']:
    obj=bpy.data.objects[name]
    vertices=[v.co for v in obj.data.vertices]
    row={'name':name,'min':[min(v[i] for v in vertices) for i in range(3)],'max':[max(v[i] for v in vertices) for i in range(3)],'uvs':[uv.name for uv in obj.data.uv_layers],'matrix':[list(r) for r in obj.matrix_world]}
    row['slices']=[]
    for z in [0,-.005,-.01,-.02,-.03,-.04,-.05,-.06,-.07,-.08,-.09,-.10]:
        pts=[v for v in vertices if abs(v.z-z)<.003]
        if pts:row['slices'].append({'z':z,'center':[sum(v[i] for v in pts)/len(pts) for i in range(3)],'count':len(pts)})
    result.append(row)
(P/'source-geometry.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
