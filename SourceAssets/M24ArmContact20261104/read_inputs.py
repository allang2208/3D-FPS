"""Capture only the active M24 profile inputs needed for authoring."""
import unreal as u, json, gzip, ast, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'serializer','exec'))
prior=json.loads((O.parent/'M24LocalMagazineGrip20261104/publish_receipt.json').read_text())
paths={v['family']:v['asset'].split('.')[0] for v in prior['saved']}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
data={}; assets={}
for family,path in paths.items():
    if path in dirty:raise RuntimeError('Unsaved input retained: '+path)
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing input: '+path)
    data[family]=packed(a,str(a.get_editor_property('family')))
    assets[family]={'path':path,'sha256':hashlib.sha256((Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')).read_bytes()).hexdigest()}
with gzip.open(O/'input_profiles.json.gz','wt',compresslevel=1) as f:json.dump(data,f,separators=(',',':'))
(O/'input_assets.json').write_text(json.dumps(assets,indent=2))
print('M24_LOCAL_GRIP_INPUTS',len(data),flush=True)

exec(compile((O/'read_clip_inputs.py').read_text(),'current base clip inputs','exec'))
