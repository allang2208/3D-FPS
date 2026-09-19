import bpy,json
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent
for variant,old in [('vertical',O.parent/'VerticalGripRaised20260911/vertical'),('prism',O.parent/'PrismGripContact20260911/prism')]:
 d=O/variant;a=json.loads((old/'fit_final.json').read_text());b=json.loads((d/'fit_final.json').read_text());release=json.loads((old/'release_profile.json').read_text())
 for e in release:
  for n,q in e['basis'].items():
   delta=Matrix(b['basis'][n]).to_quaternion()@Matrix(a['basis'][n]).to_quaternion().inverted();e['basis'][n]=list(delta@Quaternion(q))
 (d/'release_profile.json').write_text(json.dumps(release,indent=2))
 print('RELEASE_PREPARED',variant)
