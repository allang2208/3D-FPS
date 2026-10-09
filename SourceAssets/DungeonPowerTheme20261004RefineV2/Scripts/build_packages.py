"""Package new scene files without intermediate backups or unrelated workspace files."""
import json,zipfile,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];TOP=R.parents[1];OUT=TOP.parent/'power-theme-packages-r2';OUT.mkdir(exist_ok=True)
ignored={'.blend1','.blend2','.pyc'}
def allfiles():
 return sorted(p for p in TOP.rglob('*') if p.is_file() and p.suffix not in ignored and '__pycache__' not in p.parts and not p.name.endswith('.log'))
def archive(name,files):
 p=OUT/name
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for f in files:z.write(f,f.relative_to(TOP).as_posix())
 h=hashlib.sha256(p.read_bytes()).hexdigest();result=dict(file=str(p),bytes=p.stat().st_size,sha256=h,files=len(files));print(json.dumps(result),flush=True);return result
files=allfiles();thin=[]
for p in files:
 rel=p.relative_to(R) if R in p.parents else None
 if rel is None:thin.append(p);continue
 if rel.parts[0] in ('Scripts','Config','Docs','Receipts'):thin.append(p)
 elif rel.parts[0]=='Authored' and (p.suffix=='.fbx' or p.name=='manifest.json' or 'Textures' in rel.parts):thin.append(p)
 elif rel.parts[0]=='References' and p.suffix.lower() in ('.json','.txt','.md','.py','.h','.cpp','.ush'):thin.append(p)
# Generated FBX is delivered completely in the import archive; the editable
# source retains the full .blend, all original input FBX/maps, and regeneration
# scripts without redundantly carrying the same large derived geometry twice.
sourcefiles=[p for p in files if not (p.parent==R/'Authored' and p.suffix.lower()=='.fbx')]
res=[archive('PowerCenter_UE_Import_20261004.zip',thin),archive('PowerCenter_Editable_Source_20261004.zip',sourcefiles)]
(OUT/'packages.json').write_text(json.dumps(res,indent=2));print('POWER_PACKAGES_WRITTEN',flush=True)
