"""Stage only the local Epic FootOut donors; never replace an existing package."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/FPS3D/游戏动画示例/Content')
BASE = Path('Characters/UEFN_Mannequin/Animations/Slide')
OUT = ROOT/'SourceAssets/ThirdPersonSlide20261005'
ROLES = {
    'Enter.L': 'Into_Lfoot', 'Enter.R': 'Into_Rfoot',
    'Enter.Sprint.L': 'Into_Sprint_Lfoot', 'Enter.Sprint.R': 'Into_Sprint_Rfoot',
    'Loop': 'Loop', 'Exit.Stand': 'Out_Idle_Stand', 'Exit.Crouch': 'Out_Idle_Crouch',
    'Exit.CrouchMove': 'Out_Moving_Crouch', 'Exit.Walk': 'Out_Moving_Walk',
    'Exit.Run': 'Out_Moving_Run', 'Exit.Sprint': 'Out_Moving_Sprint',
}
OUT.mkdir(parents=True, exist_ok=True)
clips = {}; files = []
for role, suffix in ROLES.items():
    name = 'M_Relaxed_Slide_FootOut_'+suffix
    relative = BASE/(name+'.uasset')
    src, dst = SOURCE/relative, ROOT/'Content'/relative
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists():
        if hashlib.sha256(dst.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Existing project package differs: '+str(dst))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    clips[role] = '/Game/'+relative.with_suffix('').as_posix()
    files.append({'path':relative.as_posix(), 'sha256':digest})
data = {'source':str(SOURCE), 'provenance':'Epic Game Animation Sample; local UE-only source. Source and derived binary assets stay local.',
        'clips':clips, 'files':files}
(OUT/'donors.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
print('SLIDE_DONORS_STAGED',len(clips))
