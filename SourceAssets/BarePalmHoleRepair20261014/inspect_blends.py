import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parents[1]
files=list((P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable').glob('*.blend'))
reports=[]
for f in files:
 bpy.ops.wm.open_mainfile(filepath=str(f))
 row={'path':str(f),'meshes':[]}
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles()
  row['meshes'].append(dict(name=o.name,vertices=len(o.data.vertices),triangles=len(o.data.loop_triangles)))
 reports.append(row)
(R/'blend_sources.json').write_text(json.dumps(reports,indent=2))
print('BARE_SOURCE_BLEND_COUNTS',json.dumps(reports),flush=True)
