"""Stage the local Epic GASP crouch donors without overwriting project packages."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/FPS3D/游戏动画示例/Content')
BASE = Path('Characters/UEFN_Mannequin')
OUT = ROOT / 'SourceAssets/ThirdPersonCrouch20261005'
OUT.mkdir(parents=True, exist_ok=True)
names = ['M_Neutral_Crouch_Loop_' + d for d in ('F', 'FR', 'RR', 'RL', 'BR', 'B', 'BL', 'LL', 'LR', 'FL')]
names += ['M_Neutral_Transition_Stand_to_Crouch', 'M_Neutral_Transition_Crouch_to_Stand']
clips = {n: BASE/'Animations/Crouch'/(n+'.uasset') for n in names}
clips['M_Neutral_Crouch_Idle_Loop'] = BASE/'Animations/Idle/M_Neutral_Crouch_Idle_Loop.uasset'
files = list(clips.values())
for folder in ('Meshes', 'Materials', 'Textures'):
    files += [p.relative_to(SOURCE) for p in (SOURCE/BASE/folder).glob('*.uasset')]
files.append(BASE/'Rigs/PA_UEFN_Mannequin.uasset')
manifest = []
for relative in files:
    src, dst = SOURCE/relative, ROOT/'Content'/relative
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists():
        if hashlib.sha256(dst.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Existing project package differs: '+str(dst))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    manifest.append({'path':relative.as_posix(), 'sha256':digest})
data = {'source':str(SOURCE), 'provenance':'Epic Game Animation Sample, locally owned source; see Docs/gasp-traversal-20260910.md. Source and derived UE binaries stay local.',
        'clips':{n:'/Game/'+p.with_suffix('').as_posix() for n,p in clips.items()}, 'files':manifest}
(OUT/'donors.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
print('GASP crouch donors staged:',len(clips),'animations;',len(files),'packages')
