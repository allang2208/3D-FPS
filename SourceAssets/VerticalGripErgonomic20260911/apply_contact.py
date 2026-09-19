import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O));from fit_pose import apply,solve_arm,measure
from inspect_reference import setup_render
for variant in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);p={n:Matrix(x) for n,x in json.loads((d/'contact_solution.json').read_text())['pose'].items()};rest={b.name:b.matrix_local.copy() for b in r.data.bones};solve_arm(p,rest,p['hand_l'],G);apply(r,p,rest)
 result=measure(r,G,'VG_' if variant=='vertical' else 'PH_');(d/'fitted_measure.json').write_text(json.dumps(result,indent=2));print('EXACT',variant,result,flush=True)
 fit['hand_in_root']=[list(x) for x in p['WPN_root'].inverted()@p['hand_l']];fit['basis']={b.name:[list(x) for x in b.matrix_basis] for b in r.pose.bones if b.name.startswith(('index','middle','ring','pinky','thumb')) and b.name.endswith('_l')};(d/'fit_final.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(d/'Contact.blend'));setup_render(r,G,'contact_'+variant)
