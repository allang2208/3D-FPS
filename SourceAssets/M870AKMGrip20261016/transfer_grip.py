"""Reuse the shipped AKM grip as one complete hand; no individual-digit fit."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;BASE=O.parent/'M870SurfaceFit20261016'
d=json.loads((O/'akm_grip.json').read_text());sr={n:Matrix(m) for n,m in d['rest'].items()};sp={n:Matrix(m) for n,m in d['pose'].items()}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'M870_SurfaceFit_Editable.blend'),use_scripts=False);r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
tr={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
def frame(p):
 f=(p['middle_01_l'].translation-p['hand_l'].translation).normalized();a=(p['index_01_l'].translation-p['pinky_01_l'].translation).normalized();n=a.cross(f).normalized();a=f.cross(n).normalized()
 return Matrix((a,f,n)).transposed().to_4x4()
source_bind=frame(sr);source_pose=frame(sp);target_bind=frame(tr)
hand_q=(source_pose@target_bind.inverted()@tr['hand_l']).to_quaternion()
grip={'hand_l':Matrix.LocRotScale(sp['hand_l'].translation,hand_q,Vector((1,1,1)))}
for b in r.data.bones:
 n=b.name
 if not(n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))):continue
 par=parents[n];lr=tr[par].inverted()@tr[n]
 correction=(source_bind.inverted()@sr[n]).to_quaternion().inverted()@(target_bind.inverted()@tr[n]).to_quaternion()
 q=source_pose.to_quaternion()@(source_pose.inverted()@sp[n]).to_quaternion()@correction
 grip[n]=Matrix.LocRotScale((grip[par]@lr).translation,q,Vector((1,1,1)))
knuckles=[f'{n}_01_l' for n in ('index','middle','ring','pinky')]
delta=sum((sp[n].translation for n in knuckles),Vector())/4-sum((grip[n].translation for n in knuckles),Vector())/4
# Measured Soviet fore-end at the grip section: X centre -0.8 mm,
# Y 280 mm, lower wood surface Z 25.5 mm. Align the lower support surface.
# M870 pump lower surface Z -782.1 mm, grip section Y 230 mm.
delta+=Vector((-.0092,-.05,-.8106))
for m in grip.values():m.translation+=delta
report={'grip':{n:[list(v) for v in m] for n,m in grip.items()},'source':d['runtime_animation'],'source_action':d['action'],'method':'Whole AKM idle hand transferred by anatomical bind-frame correction. Native lengths/local offsets retained. Whole-hand knuckle-row and lower fore-end surface alignment only.','individual_digit_optimization':False,'contact_translation':list(delta)}
(O/'transferred_grip.json').write_text(json.dumps(report,indent=2));print('AKM_HAND_TRANSFERRED',len(grip),'contact_translation',list(delta))
