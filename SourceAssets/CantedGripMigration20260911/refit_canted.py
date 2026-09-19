import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(O))
from audit_m4 import OLD,support,render,apply
scope=globals();code=(O/'build_akm.py').read_text();exec(code[code.index('def arm('):code.index('def render(')],scope)
src=(S/'VerticalGripErgonomic20260911/fit_pose.py').read_text();exec(src[src.index('def measure('):src.index("if __name__=='__main__':")],globals())
import itertools
from mathutils.bvhtree import BVHTree
fit=json.loads((OLD/'fit_final.json').read_text());vfit=json.loads((S/'VerticalGripErgonomic20260911/vertical/fit_final.json').read_text());B=Matrix(fit['grip_matrix']).inverted()@Matrix(json.loads((OLD/'body_frame.json').read_text()))
bpy.ops.wm.open_mainfile(filepath=str(OLD/'A_M4_Canted_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};r.animation_data.action=None
G=p['WPN_root']@Matrix(fit['grip_in_root']);H=G@B@Matrix(vfit['grip_in_root']).inverted()@Matrix(vfit['hand_in_root'])
A=p['upperarm_l'].translation;l1=(p['lowerarm_l'].translation-A).length;l2=(p['hand_l'].translation-p['lowerarm_l'].translation).length;desired=H.to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();E=H.translation-desired*l2;delta=(E+(A-E).normalized()*l1-A)*.7
metric=arm(p,rest,H,1,delta)
for b in r.pose.bones:
 if b.name in vfit['basis']:p[b.name]=p[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name]@Matrix(vfit['basis'][b.name])
apply(r,p,rest);metric.update(measure(r,G,'CG_'));print('REFIT',metric,flush=True)
fit['hand_in_root']=[list(x) for x in p['WPN_root'].inverted()@H];fit['basis']=vfit['basis'];fit['body_in_grip']=[list(x) for x in B];fit['shoulder_offset_from_old_m']=list(delta)
fit['shoulder_in_grip']=list(G.inverted()@p['upperarm_l'].translation)
fit['attachment_local']={ob.name:[list(x) for x in G.inverted()@ob.matrix_world] for ob in s.objects if ob.name.startswith('CG_')}
(O/'canted_refit.json').write_text(json.dumps(fit,indent=2));(O/'canted_refit_measure.json').write_text(json.dumps(metric,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'));render(r,G,'refit')
