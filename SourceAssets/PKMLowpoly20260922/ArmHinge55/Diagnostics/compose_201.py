"""Full-bone tracks of the installed 201 cloth reloads: ClothReload44 (+BeltFit53) keys with the
ArmHinge55 left-arm overrides, written for the ClothReload44 offline tools."""
import json, gzip, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
C44 = HERE.parents[1] / 'LMG20120260927' / 'ClothReload44'
OUT = HERE / 'Diagnostics'
for fam in sys.argv[1:] or ['base']:
    for suffix, clip in (('', 'reload'), ('_empty', 'reload_empty')):
        with gzip.open(C44 / 'Tracks' / (fam + suffix + '_b53_tracks.json.gz'), 'rt', encoding='utf8') as f:
            full = json.load(f)
        hinge = HERE / 'Tracks' / ('ClothReload44__%s__A_LMG201_%s_%s.json.gz' % (fam, fam, clip))
        with gzip.open(hinge, 'rt', encoding='utf8') as f:
            h = json.load(f)
        for n, rows in h['tracks'].items():
            assert len(rows) == len(full[n]), n
            full[n] = rows
        with gzip.open(OUT / ('%s_%s_current.json.gz' % (fam, clip)), 'wt', encoding='utf8') as f:
            json.dump(full, f, separators=(',', ':'))
        print('COMPOSED', fam, clip, len(h['tracks']))
