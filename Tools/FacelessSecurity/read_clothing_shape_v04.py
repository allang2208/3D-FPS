"""Read source-space garment extents for the reported waist protrusions."""
import bpy,json,numpy as np
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
OUT=BASE/'V04';(OUT/'Logs').mkdir(parents=True,exist_ok=True)
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_character.py').read_text(encoding='utf-8').split('# Appended to the native skeleton')[0]
ns={};exec(compile(src,'security_fit_read','exec'),ns);fit=ns['matrix']
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V03/Authoring/FacelessSecurity_V03.blend'))
report={}
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.name in ['Security_CompleteBody','Security_OutfitBody']:continue
    names={g.index:g.name for g in o.vertex_groups}
    points=np.array([fit({names[g.group]:g.weight for g in v.groups})@v.co for v in o.data.vertices])
    edges=np.array([e.vertices[:] for e in o.data.edges]);length=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    report[o.name]={'vertices':len(points),'bounds':[points.min(0).tolist(),points.max(0).tolist()],
        'longest_edge':float(length.max()),'long_edges':int(np.sum(length>.10))}
(OUT/'source_shape_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({n:r for n,r in report.items() if n.startswith(('Security_Belt','Security_DutyBelt','Security_Buckle','Security_Collar','Security_Shirt_Continuous','Security_Trousers_Continuous'))}),flush=True)
