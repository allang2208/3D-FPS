"""Record a completed Editor build containing the M870 presentation changes."""
import hashlib,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
log=Path(sys.argv[1]).resolve();binary=ROOT/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
text=log.read_text(encoding='utf-8-sig',errors='replace')
if 'Result: Succeeded' not in text or 'FPSGAMEEditor Win64 Development' not in text:
    raise RuntimeError('A completed successful Editor build is required.')
sources={}
for name in ('Characters/FPSBodyRifleStockContacts.h','Characters/FPSBodyRifleHold.cpp',
             'Characters/FPSPlayerBodyMotion.cpp','Weapons/TacticalDeviceComponent.cpp'):
    path=ROOT/'Source/FPSGAME'/name
    if not path.stat().st_mtime<=binary.stat().st_mtime<=log.stat().st_mtime:
        raise RuntimeError('The build does not cover the current source: '+name)
    sources[str(path)]=dict(mtime=path.stat().st_mtime,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
receipt=dict(status='Succeeded',target='FPSGAMEEditor Win64 Development',log=str(log),binary=str(binary),
    binary_mtime=binary.stat().st_mtime,sources=sources,asset_writes=False,runtime_tested=False)
(OUT/'completed-build.json').write_text(json.dumps(receipt,indent=2))
(OUT/'completed-build.log').write_text(text,encoding='utf-8')
print('M870_THIRD_PERSON_BUILD_RECORDED '+str(log))
