"""Stage three locally owned full-body GASP donors without replacing packages."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/FPS3D/游戏动画示例/Content')
OUT = ROOT / 'SourceAssets/ThirdPersonTraversal20261012'
BASE = Path('Characters/UEFN_Mannequin/Animations/Traversal')
CLIPS = {
    'Vault': 'Vault/M_Neutral_Traversal_Vault_1_0_stand_F_Lfoot',
    'Mantle': 'Mantle/M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot',
    'Climb': 'Climb/M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot',
}
OUT.mkdir(parents=True, exist_ok=True)
manifest = []
paths = {}
for role, name in CLIPS.items():
    relative = BASE / (name + '.uasset')
    source, dest = SOURCE / relative, ROOT / 'Content' / relative
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Existing donor differs; preserving it: ' + str(dest))
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    paths[role] = '/Game/' + relative.with_suffix('').as_posix()
    manifest.append({'path': relative.as_posix(), 'sha256': digest})
(OUT / 'donors.json').write_text(json.dumps({
    'source': str(SOURCE), 'clips': paths, 'files': manifest,
    'provenance': 'Epic Game Animation Sample, existing local library. See Docs/gasp-traversal-20260910.md. Source and derived binaries remain local.',
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('TRAVERSAL_DONORS_STAGED', len(paths))
