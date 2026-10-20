"""Read-only refresh of current native V9 geometry; do not save UE assets."""
from pathlib import Path
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
code=(R9/'collect_inputs.py').read_text().split("profile_path=")[0]
code=code.replace("I=O/'Inputs'","I=O/'CurrentGeometry'")
code=code.replace("manifest={}","ASSETS={'arms':ASSETS['arms']}\nmanifest={}")
exec(compile(code,str(R9/'collect_inputs.py'),'exec'),globals())
(I/'manifest.json').write_text(json.dumps(manifest,indent=2))
old=json.load(gzip.open(R9/'Inputs/arms.json.gz','rt'));new=json.load(gzip.open(I/'arms.json.gz','rt'))
report={key:old[key]==new[key] for key in old if key not in ('sha256',)}
report['normalized_weights']=all(dict(a)==dict(b) for a,b in zip(old['weights'],new['weights'])) and len(old['weights'])==len(new['weights'])
(O/'native_v9_geometry_comparison.json').write_text(json.dumps({'previous_sha256':old['sha256'],'current_sha256':new['sha256'],'unchanged_fields':report},indent=2))
print('SVCH_CURRENT_V9_COMPARISON',json.dumps(report),flush=True)
