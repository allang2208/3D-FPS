"""Keep a complete source with the currently installed animations and R11 delta."""
from pathlib import Path
import gzip,json,hashlib,shutil
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';I=O/'Inputs';I.mkdir(exist_ok=True)
for name in ('svch.json.gz','arms.json.gz'):
 if not (I/name).exists():shutil.copy2(R9/'Inputs'/name,I/name)
if (O/'CurrentGeometry/arms.json.gz').exists():
 current=json.load(gzip.open(O/'CurrentGeometry/arms.json.gz','rt'));old=json.load(gzip.open(R9/'Inputs/arms.json.gz','rt'))
 assert all(current[k]==old[k] for k in current if k not in ('sha256','weights'))
 assert len(current['weights'])==len(old['weights']) and all(dict(a)==dict(b) for a,b in zip(current['weights'],old['weights']))
 shutil.copy2(O/'CurrentGeometry/arms.json.gz',I/'arms.json.gz')
shutil.copy2(O/'CurrentSource/motion.json.gz',I/'motion.json.gz')
code=(R9/'export_editable.py').read_text().replace('profile_reload_grip.json','profile_charge.json').replace('SVCH_R9_','SVCH_R11_')
exec(compile(code,str(R9/'export_editable.py'),'exec'),{'__file__':__file__})
file=O/'editable_source.json';report=json.loads(file.read_text());report['profile_source_sha256']=hashlib.sha256((O/'profile_charge.json').read_bytes()).hexdigest();file.write_text(json.dumps(report,indent=2))
