"""Reuse the surface probe on candidate idle and departure/return samples."""
from pathlib import Path
import json,sys
SOURCE=Path(__file__).parent
O=SOURCE/'Final'
build=json.loads((O/'build.json').read_text())
for weapon in ['m4','akm']:
 d=O/weapon/'vertical'
 (d/('animation_build.json' if weapon=='m4' else 'build.json')).write_text(json.dumps({key.split(':')[1]:v for key,v in build.items() if key.startswith(weapon+':')},indent=2))
template=(SOURCE.parent/'VerticalGripFront20260911/ReferenceWorkflow/check_geometry.py').read_text()
template=template.replace('O=Path(__file__).parent','O=ROOT').replace('"Canted" if weapon=="m4" else variant','variant.title() if weapon=="m4" else variant').replace("x.name.startswith('CG_')","x.name.startswith('VG_')")
start=template.index(" if 'reload' not in clip:frames=")
finish=template.index(' parts=',start)
template=template[:start]+''' if 'reload' not in clip:frames=[0,end/2,end]
 elif weapon=='m4':frames=sorted(set([0,3,6,9,12,15,16,20,24,28,end-24,end-20,end-16,end-12,end-9,end-6,end-3,end]))
 else:
  start=380 if 'empty' in clip else 270
  frames=sorted(set([0,6,12,18,24,30,36,42,start,start+10,start+20,start+30,start+36,start+42,start+48,start+54,start+60,end]))
'''+template[finish:]
ROOT=O
exec(compile(template,str(O/'probe_generated.py'),'exec'))
