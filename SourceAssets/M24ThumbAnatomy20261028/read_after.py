import unreal as u,json,ast
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O/'install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')
exec(compile(ast.unparse(fn),'profile_readback','exec'))
result={}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name)
 if not p:raise RuntimeError('Cannot read saved profile '+name)
 result[family]=packed(p,family)
(O/'ue_after_profiles.json').write_text(json.dumps(result));print('M24_THUMB_PROFILES_READ_BACK',flush=True)
