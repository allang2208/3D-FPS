"""Back-to-back pack: what is in the game now  vs  the second-generation rebuild.

`1_*` is the asset currently installed (what the user just tested and still heard
BGM in), `2_*` is the new rebuild, `3_*`/`4_*` are the replaced and replacement
tail alone.  The decisive comparison is 3 vs 4: the old tail sat at, or above,
the bed; the new one sits 12-22 dB below it and decays away.
"""
import json
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
OUT = HERE / 'out2'
PACK = OUT / '_listening'
PACK.mkdir(parents=True, exist_ok=True)
RATE = 48000

old_manifest = json.loads((PARENT / 'tail_repair_manifest.json').read_text(encoding='utf-8'))
installed = {r['asset_name']: PARENT / r['wav'] for r in old_manifest['repairs']}
CHARGE = ('ChargePullMove', 'ChargeRearStop', 'ChargePushMove', 'ChargeFrontStop')


def installed_path(name):
    p = installed.get('S_PKM_%s' % name)
    if p and p.is_file():
        return p
    return (PARENT / f'S_PKM_{name}.wav') if name not in CHARGE \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')


def loop(v, n):
    return np.tile(v, n)


def align(v, target):
    p = float(np.max(np.abs(v)))
    return v * (target / p) if p > 0 else v


report = json.loads((OUT / 'debgm2_report.json').read_text(encoding='utf-8'))
items = []
for r in report['rows']:
    if r['action'] != 'rebuilt':
        continue
    name = r['clip']
    before = np.asarray(sf.read(installed_path(name))[0], dtype=np.float64)
    after = np.asarray(sf.read(OUT / f'S_PKM_{name}_debgm2.wav')[0], dtype=np.float64)
    old_tail = np.asarray(sf.read(OUT / f'_{name}_tail_OLD.wav')[0], dtype=np.float64)
    new_tail = np.asarray(sf.read(OUT / f'_{name}_tail_NEW.wav')[0], dtype=np.float64)
    tgt = max(float(np.max(np.abs(before))), float(np.max(np.abs(after))))
    sf.write(PACK / f'1_{name}_IN_GAME_now.wav', loop(align(before, tgt), 3), RATE, subtype='PCM_16')
    sf.write(PACK / f'2_{name}_NEW.wav', loop(align(after, tgt), 3), RATE, subtype='PCM_16')
    tp = max(float(np.max(np.abs(old_tail))), float(np.max(np.abs(new_tail))), 1e-9)
    sf.write(PACK / f'3_{name}_tail_IN_GAME.wav', loop(align(old_tail, tp), 4), RATE, subtype='PCM_16')
    sf.write(PACK / f'4_{name}_tail_NEW.wav', loop(align(new_tail, tp), 4), RATE, subtype='PCM_16')
    items.append({'clip': name, 'rebuilt_ms': r['rebuilt_ms'],
                  'bed_band_suppression_db': next(
                      (v['bed_band_suppression_db'] for v in json.loads(
                          (OUT / 'verification2.json').read_text(encoding='utf-8'))
                       if v.get('clip') == name), None)})

# whole-reload sequence, so the bed's behaviour across the eight cues is audible
seq_old, seq_new = [], []
ORDER = ['CoverOpen', 'BeltLift', 'BoxOut', 'BoxInsert', 'BeltSeat', 'CoverClose']
for name in ORDER:
    p = installed_path(name)
    n = OUT / f'S_PKM_{name}_debgm2.wav'
    if n.is_file():
        seq_old.append(np.asarray(sf.read(p)[0], dtype=np.float64))
        seq_new.append(np.asarray(sf.read(n)[0], dtype=np.float64))
g = 0.06 * RATE
sil = np.zeros(int(g))
for label, parts in (('reload_sequence_IN_GAME_now', seq_old), ('reload_sequence_NEW', seq_new)):
    out = []
    for i, s in enumerate(parts):
        out.append(s)
        if i < len(parts) - 1:
            out.append(sil)
    v = np.concatenate(out)
    p = float(np.max(np.abs(v)))
    sf.write(PACK / f'5_{label}.wav', v * (0.9 / p), RATE, subtype='PCM_16')

(PACK / 'listen_manifest.json').write_text(json.dumps({
    '1_vs_2': 'the installed asset vs the new rebuild, 3 loops each, peak-aligned',
    '3_vs_4': 'the replaced tail vs the replacement, 4 loops each -- the decisive pair',
    '5': 'the whole six-contact reload in order, 60 ms apart, so the music bed across cues is audible',
    'note': 'Offline authoring only. No listening was performed by the author.',
    'items': items}, indent=2), encoding='utf-8')
print('pack ->', PACK)
for f in sorted(PACK.glob('*.wav')):
    print(' ', f.name, f.stat().st_size)