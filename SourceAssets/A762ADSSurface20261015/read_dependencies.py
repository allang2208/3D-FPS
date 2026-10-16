import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R=json.loads((O/'recipe.json').read_text());out={}
for t in R['targets']:
 if t['clone']:continue
 refs=u.EditorAssetLibrary.find_package_referencers_for_asset(t['source'].split('.')[0],False)
 out[t['source']]=[str(x) for x in refs]
(O/'references.json').write_text(json.dumps(out,indent=2))
external={k:[p for p in v if '/A762/' not in p] for k,v in out.items()}
print('A762_MATERIAL_SHARED_REFERENCES',json.dumps({k:v for k,v in external.items() if v}))
