import unreal as u,json,ast,math
from pathlib import Path
O=Path(__file__).resolve().parent;tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
patch=json.loads((O/'profile_patch.json').read_text());output={};report={}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
    profile=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name);clips=packed(profile,family)['clips'];output[family]=clips;error=0.
    for path in patch['modified'][family]:
        live=next(c for c in clips if c['base']==path);want=next(c for c in patch['profiles'][family] if c['base']==path)
        by_name={t['bone']:t for t in live['tracks']}
        for target in want['tracks']:
            actual=by_name[target['bone']]
            for field in ('times','values'):
                if len(actual[field])!=len(target[field]):raise RuntimeError('Track key count mismatch')
                error=max(error,max((abs(a-b) for a,b in zip(actual[field],target[field])),default=0.))
    if error>1e-4:raise RuntimeError('Saved profile mismatch '+str(error))
    report[family]={'profile':profile.get_path_name(),'modified_clips_found':len(patch['modified'][family]),'max_saved_float_error':error}
(O/'profiles_saved.json').write_text(json.dumps(output));(O/'readback.json').write_text(json.dumps(report,indent=2));print('M24_IDLE_READBACK',json.dumps(report),flush=True)
