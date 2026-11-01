import unreal as u,json,gzip,ast
from pathlib import Path
O=Path(__file__).resolve().parent
before=json.load(gzip.open(O/'before.json.gz','rt'))
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
out={family:packed(u.load_asset(path),family) for family,path in before['paths'].items()}
with gzip.open(O/'saved_profiles.json.gz','wt') as f:json.dump(out,f)
print('M24_ARM_ROOT_DISK_READBACK',len(out),flush=True)
