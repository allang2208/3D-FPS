"""Re-apply the BeltFit53 belt/link patch (SourceAssets/LMG20120260927/BeltFit53/motion.py,
read-only) to ClothReload44 tracks, and merge it into full clip tracks for install.py.

python -X utf8 apply_b53_belt.py empty      -> B53 on the ClothReload44.4 empty clips
python -X utf8 apply_b53_belt.py normal     -> merge BeltFit53/Tracks (its exact output) onto the normal tracks

The empty clip only differs in its source clock: B53's new-belt seating window (4.38-4.78 s
on the normal clip) is mapped through author_motion.EMPTY_KNOTS, like the runtime
LMG201WeaponAssets::ClothEventTime.  BeltFit53 files are only read, never written.
"""
import sys, json, gzip
from pathlib import Path

HERE = Path(__file__).resolve().parent
B53 = HERE.parent / 'BeltFit53'
OUT = HERE / 'B53Patch'
OUT.mkdir(exist_ok=True)
FAMS = ['base', 'vertical', 'canted', 'prism', 'angled']
KNOTS = ((1.46, 1.46), (2.00, 1.80), (5.45, 5.46), (6.2, 6.2))


def empty_time(t):
    if t <= KNOTS[0][0]:
        return t
    for (a, ea), (b, eb) in zip(KNOTS, KNOTS[1:]):
        if t <= b:
            return ea + (t - a) * (eb - ea) / (b - a)
    return t


def merge(base_path, patch_path, out_path):
    with gzip.open(base_path, 'rt', encoding='utf8') as f:
        full = json.load(f)
    with gzip.open(patch_path, 'rt') as f:
        patch = json.load(f)
    for n, rows in patch.items():
        assert 'LMG201_Belt_' in n and n in full and len(rows) == len(full[n]), n
        full[n] = rows
    with gzip.open(out_path, 'wt', encoding='utf8') as f:
        json.dump(full, f, separators=(',', ':'))
    return len(patch)


mode = sys.argv[1] if len(sys.argv) > 1 else 'empty'
if mode == 'normal':
    for fam in FAMS:
        n = merge(HERE / 'Tracks' / (fam + '_tracks.json.gz'), B53 / 'Tracks' / (fam + '_tracks.json.gz'),
                  HERE / 'Tracks' / (fam + '_b53_tracks.json.gz'))
        print('B53_MERGED normal', fam, n, flush=True)
    raise SystemExit(0)

src = (B53 / 'motion.py').read_text(encoding='utf-8-sig')
rep = [
    ("O=Path(__file__).parent;", "O=B53_DIR;"),
    ("(O/'Tracks').mkdir(exist_ok=True)", "OUT_DIR.mkdir(exist_ok=True)"),
    ("for family in (sys.argv[1:] or ['base','vertical','canted','prism','angled']):",
     "for family in FAMILIES:"),
    ("path=O.parent/'ClothReload44/Tracks'/(family+'_tracks.json.gz')",
     "path=TRACK_DIR/(family+'_empty_tracks.json.gz')"),
    ("seat=smooth((t-4.38)/.40) if side else", "seat=smooth((t-ET(4.38))/(ET(4.78)-ET(4.38))) if side else"),
    ("with gzip.open(O/'Tracks'/(family+'_tracks.json.gz'),'wt') as f:",
     "with gzip.open(OUT_DIR/(family+'_empty_tracks.json.gz'),'wt') as f:"),
    ("with gzip.open(O/(family+'_points.json.gz'),'wt') as f:", "with gzip.open(OUT_DIR/(family+'_empty_points.json.gz'),'wt') as f:"),
    ("(O/'motion.json').write_text(json.dumps(report,indent=2))", "(OUT_DIR/'b53_empty_patch.json').write_text(json.dumps(report,indent=2))"),
]
for a, b in rep:
    assert src.count(a) == 1, a
    src = src.replace(a, b)
g = {'__name__': 'b53_on_empty', '__file__': str(B53 / 'motion.py'), 'B53_DIR': B53, 'OUT_DIR': OUT,
     'TRACK_DIR': HERE / 'Tracks', 'FAMILIES': FAMS, 'ET': empty_time}
exec(compile(src, str(B53 / 'motion.py') + ' (ClothReload44 empty)', 'exec'), g)
for fam in FAMS:
    n = merge(HERE / 'Tracks' / (fam + '_empty_tracks.json.gz'), OUT / (fam + '_empty_tracks.json.gz'),
              HERE / 'Tracks' / (fam + '_empty_b53_tracks.json.gz'))
    print('B53_MERGED empty', fam, n, flush=True)
