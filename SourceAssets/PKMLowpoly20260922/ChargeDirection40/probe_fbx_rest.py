"""Does an imported PKM FBX keep the same rest frame as the author rig?

If yes, the validated Elbow39 roll metric can be run directly on any clip's FBX
without hunting for its authoring blend.
"""
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'

author = np.load(ROOT / 'Elbow39' / 'author_rig.npz', allow_pickle=True)
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}

PROBE = ['upperarm_l', 'lowerarm_l', 'lowerarm_twist_02_l', 'hand_l']

for tag, fbx in (('idle', ROOT / 'Elbow39' / 'Exports' / 'A_PKM_idle.fbx'),
                 ('sprint_enter', ROOT / 'Combat17' / 'Animations' / 'base' / 'A_PKM_sprint_enter.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False)
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    print('\n===', tag, 'rig', rig.name, 'bones', len(rig.data.bones),
          'scale', tuple(round(v, 4) for v in rig.scale))
    for n in PROBE:
        if n not in rig.data.bones:
            print('  %-22s MISSING' % n)
            continue
        a = np.array(rig.data.bones[n].matrix_local)
        b = AU_REST[AU_INDEX[n]]
        ta, tb = a[:3, 3], b[:3, 3]
        la, lb = np.linalg.norm(ta), np.linalg.norm(tb)
        ra = a[:3, :3]
        rb = b[:3, :3]
        # best uniform scale between the two rests
        s = float(np.trace(ra.T @ rb) / np.trace(ra.T @ ra)) if np.trace(ra.T @ ra) else 0.0
        resid = float(np.abs(ra * s - rb).max())
        print('  %-22s |t_fbx| %8.4f |t_au| %8.4f ratio %7.3f | rot residual %7.5f'
              % (n, la, lb, (la / lb if lb else 0.0), resid))
print('\nREST_PROBE_DONE')