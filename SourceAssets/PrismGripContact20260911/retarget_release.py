import bpy,json
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent;p=O/'prism';old=O.parent/'VerticalGripRaised20260911/prism';a=json.loads((old/'fit_final.json').read_text());b=json.loads((p/'fit_final.json').read_text());release=json.loads((old/'release_profile.json').read_text())
for e in release:
 for n,q in e['basis'].items():
  delta=Matrix(b['basis'][n]).to_quaternion()@Matrix(a['basis'][n]).to_quaternion().inverted();e['basis'][n]=list(delta@Quaternion(q))
(p/'release_profile.json').write_text(json.dumps(release,indent=2))
