from pathlib import Path
import unreal as u,json,gzip,hashlib,ast
O=Path(__file__).resolve().parent
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List
src=O.parent/'SkeletonSniperStock20261031/Review20261031/read_assets.py'
for n in ast.parse(src.read_text()).body:
    if isinstance(n,ast.FunctionDef):exec(compile(ast.unparse(n),str(src),'exec'))
meta=json.loads((O/'Inputs/current.json').read_text())
data=read(meta['host']['path'])
with gzip.open(O/'Inputs/host.json.gz','wt') as f:json.dump(data,f)
print('M24_HOST_GEOMETRY',len(data['triangles']),data['bones'].get('WPN_root'))
