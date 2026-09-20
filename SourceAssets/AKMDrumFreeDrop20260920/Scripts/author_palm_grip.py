"""Adduct and curl the AKM supporting hand without moving its palm anchor."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parents[1]
previous=json.loads((O/'Inputs/palm_support_anchor.json').read_text())
meta=json.loads((O/'source_manifest.json').read_text())['base/drum_reload']
bpy.ops.wm.open_mainfile(filepath=str(Path(meta['source'][0]).with_suffix('.blend')))
r=bpy.data.objects['SK_M4_Infima']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
names=[n for n in rest if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))]
def frame(f,n):
 f=f.normalized();z=(n-f*n.dot(f)).normalized()
 return Matrix((f,f.cross(z),z)).transposed()
H0=rest['hand_l']
normal=(rest['pinky_01_l'].translation-H0.translation).cross(rest['index_01_l'].translation-H0.translation).normalized()
reference=frame(rest['middle_01_l'].translation-H0.translation,normal)
correction=reference.inverted()@H0.to_3x3()
H=Matrix(previous['hand_in_mag']);semantic=H.to_3x3()@correction.inverted()
# Absolute segment elevations: MCP flex, then additional PIP and DIP flex.
# Keep four fingers together, allowing the short little finger to reach the
# rounded lower edge; the thumb opposes them on the other side of the drum.
digits={
 'index':{'spread':[-3,-3,-3],'flex':[59,112,124]},
 'middle':{'spread':[-1,-1,-1],'flex':[59,111,124]},
 'ring':{'spread':[-2,-2,-2],'flex':[45,106,122]},
 'pinky':{'spread':[-3,-3,-3],'flex':[32,78,98]},
 'thumb':{'spread':[-75,-80,-82],'flex':[38,73,102]},
}
p={'hand_l':H};basis={}
for n in names:
 parent=parents[n];m=p[parent]@local[n];parts=n.split('_')
 if len(parts)==3 and parts[1].isdigit():
  k=int(parts[1])-1;nxt=f'{parts[0]}_{k+2:02d}_l'
  if nxt in rest:rd=rest[nxt].translation-rest[n].translation
  else:rd=rest[n].to_quaternion()@(rest[parent].to_quaternion().inverted()@(rest[n].translation-rest[parent].translation))
  spread,flex=[math.radians(digits[parts[0]][key][k]) for key in ('spread','flex')]
  # A continuous flex frame avoids the 180-degree roll flip of projecting an
  # up vector when the finger segment passes through vertical at 90 degrees.
  target=semantic@Matrix.Rotation(spread,3,'Z')@Matrix.Rotation(-flex,3,'Y')
  rotation=target@frame(rd,normal).inverted()@rest[n].to_3x3()
  m=Matrix.LocRotScale(m.translation,rotation.to_quaternion(),Vector((1,1,1)))
 p[n]=m;basis[n]=(local[n].inverted()@p[parent].inverted()@m).to_quaternion()
result={**previous,'revision':'PalmGripV3','finger_basis':{n:list(q) for n,q in basis.items()},
 'open_finger_basis':previous['finger_basis'],'semantic_digits':digits,
 'method':'Fixed palm-up support anchor; adducted fingers with individual MCP/PIP/DIP curl and opposing thumb',
 'joint_positions_in_mag':{n:list(m.translation) for n,m in p.items()},
 'reference':'Revisions/PalmSupportV2/user_palm_support.jpg',
 'pose_review_requested':True,'game_tested':False}
for k in ('cup_strength','palm_contact_fit_gap_m'):result.pop(k,None)
(O/'contact_fit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PALM_GRIP_AUTHORED '+result['revision'],flush=True)
