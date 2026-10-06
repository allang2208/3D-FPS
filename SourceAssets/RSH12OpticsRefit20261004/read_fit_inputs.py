import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'PSO1Russian20260923/PSO1_AKM_Editable.blend'))
report={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not ob.name.startswith('PSO_'):continue
    p=[v.co for v in ob.data.vertices]
    report[ob.name]=dict(matrix=[list(r) for r in ob.matrix_world],bounds_data=[[min(v[k] for v in p) for k in range(3)],[max(v[k] for v in p) for k in range(3)]],slots=[m.name for m in ob.data.materials if m])
parts=json.loads((O.parent/'RSH12Integration20261003/canonical_parts.json').read_text())
report['gun_parts']={p['name']:[[min(v[k] for v in p['verts']) for k in range(3)],[max(v[k] for v in p['verts']) for k in range(3)]] for p in parts}
(O/'fit_inputs.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
