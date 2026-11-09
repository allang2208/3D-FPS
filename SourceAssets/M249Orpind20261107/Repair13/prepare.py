from pathlib import Path
import zipfile,json,hashlib
r=Path(__file__).resolve().parent;p=r.parents[2]
files=['Source/FPSGAME/FPSGAMECharacter.h','Source/FPSGAME/Weapons/M4MuzzleVisual.cpp','Source/FPSGAME/Weapons/M4HandstopVisual.cpp','Source/FPSGAME/Weapons/PhantomRearGripVisual.cpp','Source/FPSGAME/Weapons/SkeletonStockVisual.cpp','Source/FPSGAME/Weapons/SVDGripProfiles.cpp','Source/FPSGAME/Weapons/WeaponBipodDeploymentComponent.cpp','Source/FPSGAME/UI/ColdSteelIconResources.cpp','Content/ColdSteelData/gunsmith.json']
if (r/'before.zip').exists():raise RuntimeError('Keep original snapshot')
with zipfile.ZipFile(r/'before.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in files:z.write(p/f,f)
(r/'before_hashes.json').write_text(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files},indent=2))
print('M249 common parts source snapshot',len(files))
