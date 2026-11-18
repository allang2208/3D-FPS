"""Prepare an explicitly labeled authoring preview before saving the new clips."""
import json
import os
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'SourceAssets/ChapelFurniture20261116'
REVISION_ROOT = Path(os.environ.get('CHAPEL_FURNITURE_OUTPUT', str(BASE / 'HandsR2')))
OUT = REVISION_ROOT / 'Candidate'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
source = read(REVISION_ROOT / 'authored.json')
manifest = read(BASE / 'PreviewR1/manifest.json')
manifest['kind'] = 'authored_candidate'
manifest['production_assets_modified'] = False
for variant, rig in source['variants'].items():
    folder = OUT / variant
    folder.mkdir(exist_ok=True)
    for name in ('body.json', 'head.json'):
        if not (folder / name).exists():
            shutil.copy2(BASE / 'PreviewR1' / variant / name, folder / name)
    clips = {}
    for phase, take in rig['clips'].items():
        frames = []
        for frame in take['frames']:
            f = np.asarray(frame)
            w = np.tile(np.eye(4), (len(f), 1, 1))
            w[:, :3, :3] = R.from_quat(f[:, 3:7]).as_matrix() * f[:, None, 7:]
            w[:, :3, 3] = f[:, :3]
            for i, parent in enumerate(rig['parents']):
                if parent >= 0:
                    w[i] = w[parent] @ w[i]
            scale = np.linalg.norm(w[:, :3, :3], axis=1)
            frames.append(np.concatenate((w[:, :3, 3], R.from_matrix(w[:, :3, :3] / scale[:, None, :]).as_quat(), scale), axis=1).tolist())
        clips[phase] = {'asset': 'AUTHORING_CANDIDATE', 'duration': take['duration'], 'rate': take['rate'], 'world': frames}
    (folder / 'saved_poses.json').write_text(json.dumps({'mesh': rig['mesh'], 'names': rig['names'], 'clips': clips}, separators=(',', ':')), encoding='utf-8')
shutil.copy2(BASE / 'PreviewR1/pew.json', OUT / 'pew.json')
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('CHAPEL_HAND_CANDIDATE_PREPARED')
