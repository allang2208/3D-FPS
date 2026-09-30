"""Reuse the project arm and sprint recipes; do not run their asset writers."""
import ast,math,functools
from pathlib import Path
from mathutils import Matrix,Vector,Euler,Quaternion
S=Path(__file__).parent.parent.parent

@functools.lru_cache(maxsize=4)
def compiled_functions(path,wanted):
 tree=ast.parse(path.read_text(encoding='utf-8'))
 selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
 return compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec')
def functions(path,wanted,namespace):exec(compiled_functions(path,tuple(sorted(wanted))),namespace)

def arm_namespace(names):
 env={'math':math,'Matrix':Matrix,'Vector':Vector,'Euler':Euler,'Quaternion':Quaternion,'names':names}
 functions(S/'DanWesson71520260913/author_weapon.py',{'hand_at'},env)
 return env

def frame_xy(x,y):
 x=x.normalized();y=(y-x*y.dot(x)).normalized();z=x.cross(y).normalized()
 return Matrix((x,y,z)).transposed().to_quaternion()

def palm_across(rest):
 h=rest['hand_l'].translation;forward=(rest['middle_01_l'].translation-h).normalized()
 normal=(rest['index_01_l'].translation-h).cross(rest['pinky_01_l'].translation-h).normalized()
 # Same semantic axes as FPSCastingMeshComponent::CacheCastSkeleton.
 return normal.cross(forward).normalized()

def support_arm(original,target,rest,names,weight=1.0):
 """Accepted IK, palm-width roll, native auxiliary-bone segment relationships."""
 env=arm_namespace(names);p={n:m.copy() for n,m in target.items()}
 env['hand_at'](p,original,'l',target['hand_l'])
 # Hand/finger targets are already fitted. Only the arm is solved here.
 for n in names:
  if n.endswith('_l') and n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')):p[n]=target[n].copy()
 lower='lowerarm_l';upper='upperarm_l';hand='hand_l'
 ref_axis=rest[hand].translation-rest[lower].translation
 axis=(p[hand].translation-p[lower].translation).normalized();across=palm_across(rest)
 hand_deform=p[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
 wanted_across=hand_deform@across
 # Existing casting V5 fix: use palm width, not a full hand delta/twist angle.
 deform=frame_xy(axis,wanted_across)@frame_xy(ref_axis,across).inverted()
 roll=p[lower].to_quaternion().slerp(deform@rest[lower].to_quaternion(),weight)
 p[lower]=Matrix.LocRotScale(p[lower].translation,roll,original[lower].to_scale())
 # Existing casting V6 shoulder-roll support, bounded to its small share.
 ua=(p[lower].translation-p[upper].translation).normalized()
 current=(p[upper].to_quaternion()@rest[upper].to_quaternion().inverted())@across
 u=(current-ua*current.dot(ua)).normalized();v=(wanted_across-ua*wanted_across.dot(ua)).normalized()
 theta=max(-math.radians(12),min(math.radians(12),math.atan2(ua.dot(u.cross(v)),u.dot(v))*.18))
 p[upper]=Matrix.LocRotScale(p[upper].translation,Quaternion(ua,theta*weight)@p[upper].to_quaternion(),original[upper].to_scale())
 # This imported rifle already has an authored native twist profile. Carry
 # that complete segment, as the accepted AKM sprint hand_at does. Never add
 # another per-helper fraction or indiscriminately zero the native profile.
 for n in names:
  if n.endswith('_l') and n.startswith(('upperarm_twist','lowerarm_twist')):
   base=upper if n.startswith('upperarm') else lower
   p[n]=p[base]@original[base].inverted()@original[n]
 return p

def sprint_namespace(idle,rest,parents,names,settings):
 env=arm_namespace(names)
 env.update({'idle':idle,'rest':rest,'parent':parents,'lr':{n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names},'settings':settings,'raise_pitch':0.0})
 # The returned weapon/right-hand pose is discarded by our caller. Only the
 # existing native left-hand release/shoulder arc/relax/hang recipe is reused.
 functions(S/'RifleTacticalSprint20260915/author_sprint.py',{'smooth','turn','make_pose'},env)
 return env
