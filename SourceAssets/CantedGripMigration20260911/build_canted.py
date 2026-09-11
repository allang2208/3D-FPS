import json,sys,bpy,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).parent;S=ROOT.parent;sys.path.insert(0,str(ROOT))
from audit_m4 import support
src=(ROOT/'build_akm.py').read_text();exec(src[src.index('def arm('):src.index('def render(')],globals())
def solve_arm(p,rest,H,G,w):
 delta=G@Vector(fit['shoulder_in_grip'])-p['upperarm_l'].translation
 return arm(p,rest,H,w,delta)
source=(ROOT/'ReferenceWorkflow/m4_build_family.py').read_text()
source=source.replace('O=Path(__file__).parent',"O=ROOT/'m4/canted'").replace('BASE=O.parents[1]','BASE=S').replace('from fit_pose import solve_arm','')
exec(compile(source,str(ROOT/'m4/canted/build_generated.py'),'exec'),globals())
