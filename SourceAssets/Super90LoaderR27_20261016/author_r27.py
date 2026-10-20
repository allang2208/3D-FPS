"""R27: re-sample the R26b left-hand layer on the R27 clock (author data only).

The layer design is unchanged (push compliance in perceived pace time, peel-off,
finger trailing, hang retime 115-123 before the detach cue); only the clock that
maps its pace-time shapes onto the 60 Hz source keys is R27. Base pose is still
the pre-R26 installed clip read in Super90LoaderR26_20261016/inputs.json.
"""
import json, sys
from pathlib import Path
O = Path(__file__).parent
sys.path.insert(0, str(O))
sys.path.insert(1, str(O.parent / 'Super90LoaderR26_20261016'))
import r27_timing
sys.modules['r26_timing'] = r27_timing      # author_r26 samples its pace layers on this clock
import author_r26 as A

REVISION = 'Super90LoaderR27-20261016'


def main():
    import multiprocessing
    out = dict(revision=REVISION, fps=A.FPS, write_bones=A.WRITE, clips={},
               profiles={f: dict(path=A.D['profiles'][f]['path'], clips={}) for f in A.FAMILIES}, runtime_tested=False)
    notes = dict(revision=REVISION, clock='Super90LoaderPushTiming.h from r27_timing.py',
                 layer='R26b layer (author_r26.py) unchanged, sampled on R27', clips={}, runtime_tested=False)
    with multiprocessing.Pool(min(7, len(A.D['clips']))) as pool:
        for role, spec, layers, note in pool.imap(A.process, list(A.D['clips'])):
            out['clips'][role] = spec
            for family, layer in layers.items():
                out['profiles'][family]['clips'][spec['path']] = layer
            notes['clips'][role] = note
            print('R27_AUTHORED', role, json.dumps(dict(snap_gain=note['snap']['gain'], hang=note['hang']['window'],
                  roll=note['base']['roll_deg'], clear_drop=note['base']['clearance_drop_mm'])), flush=True)
    (O / 'animation_patch.json').write_text(json.dumps(out, separators=(',', ':')))
    (O / 'authoring.json').write_text(json.dumps(notes, indent=2))


if __name__ == '__main__':
    main()
