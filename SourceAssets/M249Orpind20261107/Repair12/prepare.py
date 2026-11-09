from pathlib import Path
import json,hashlib,zipfile
r=Path(__file__).resolve().parent;p=r.parents[2]
d=json.loads((r/'current_assets.json').read_text());files={}
for package,sha in d['hashes'].items():
    if package.startswith('/Game/Weapons/M249/'):
        rel='Content/'+package.removeprefix('/Game/')+'.uasset'
        if hashlib.sha256((p/rel).read_bytes()).hexdigest()!=sha:raise RuntimeError('Production input changed: '+rel)
        files[rel]=sha
for rel in ('Source/FPSGAME/FPSGAMECharacter.cpp','Source/FPSGAME/FPSGAMECharacter.h',
    'Source/FPSGAME/Weapons/M4GunsmithVisual.cpp','Source/FPSGAME/Weapons/WeaponSurfaceStandard.h',
    'Source/FPSGAME/UI/ColdSteelIconResources.cpp','Content/ColdSteelData/gunsmith.json',
    'SourceAssets/M249Orpind20261107/import_assets.py','SourceAssets/M249Orpind20261107/Repair08/import.py'):
    files[rel]=hashlib.sha256((p/rel).read_bytes()).hexdigest()
if (r/'before.zip').exists():raise RuntimeError('Keep existing backup')
with zipfile.ZipFile(r/'before.zip','w',zipfile.ZIP_DEFLATED) as z:
    for rel in files:z.write(p/rel,rel)
(r/'before_hashes.json').write_text(json.dumps(files,indent=2))
print('M249 surface/optic source snapshot saved',len(files))
