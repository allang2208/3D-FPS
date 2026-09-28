"""Listening pack: what is installed (v2) vs v3, per contact and as a whole reload.

`1_*` is installed, `2_*` is v3, `3_*` is what v3 removed (the bed as the gate sees
it).  Also the six-contact reload in order, so the bed's persistence across cues is
audible end to end.  Peak-aligned and looped; nothing here is imported.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
NEW = HERE / 'out3'
PACK = NEW / '_listening'
PACK.mkdir(parents=True, exist_ok=True)
RATE = 48000
CHARGE = ('ChargePullMove', 'ChargeRearStop', 'ChargePushMove', 'ChargeFrontStop')


def inst(n):
    p = PARENT / f'S_PKM_{n}.wav'
    return p if p.is_file() else PARENT.parent / 'ChargeAudio35' / f'S_PKM_{n}.wav'


def rd(p):
    return np.asarray(sf.read(p)[0], dtype=np.float64)


def align(v, t):
    p = float(np.max(np.abs(v)))
    return v * (t / p) if p > 0 else v


report = json.loads((NEW / 'debgm3_report.json').read_text(encoding='utf-8'))
ORDER = ['CoverOpen', 'BeltLift', 'BoxOut', 'BoxInsert', 'BeltSeat', 'CoverClose']
rows = []
for r in report['rows']:
    n = r['clip']
    if n not in ORDER and n not in CHARGE:
        continue
    before, after = rd(inst(n)), rd(NEW / f'S_PKM_{n}_debgm3.wav')
    rem = before - after
    pk = max(float(np.max(np.abs(before))), float(np.max(np.abs(after))))
    sf.write(PACK / f'1_{n}_INSTALLED.wav', np.tile(align(before, pk), 3), RATE, subtype='PCM_16')
    sf.write(PACK / f'2_{n}_v3.wav', np.tile(align(after, pk), 3), RATE, subtype='PCM_16')
    rp = float(np.max(np.abs(rem))) or 1e-9
    sf.write(PACK / f'3_{n}_removed_by_v3.wav',
             np.tile(rem * (pk / rp) * 0.7, 4), RATE, subtype='PCM_16')
    rows.append({'clip': n, 'bed_suppression_db': r['bed_band_suppression_db'],
                 'mean_gain_on_music_db': r['applied_gain_db_in_deep_frames'],
                 'unity_pct': r['samples_at_unity_gain_pct'],
                 'rms_delta_db': round(r['rms_after_db'] - r['rms_before_db'], 2)})

for label, src in (('INSTALLED', 'inst'), ('v3', 'new')):
    seq = []
    for i, n in enumerate(ORDER):
        seq.append(rd(inst(n)) if src == 'inst' else rd(NEW / f'S_PKM_{n}_debgm3.wav'))
        if i < len(ORDER) - 1:
            seq.append(np.zeros(int(0.06 * RATE)))
    v = np.concatenate(seq)
    sf.write(PACK / f'4_reload_sequence_{label}.wav', v * (0.9 / np.max(np.abs(v))),
             RATE, subtype='PCM_16')

(PACK / 'README.json').write_text(json.dumps({
    'question': 'does v3 remove the bed the earlier rounds left in place?',
    '1': 'installed (v2) -- what the user just rejected',
    '2': 'v3 -- whole-cue gate',
    '3': 'what v3 removed, boosted to be audible: this is the bed it found',
    '4': 'the six-contact reload in order, 60 ms apart',
    'author_note': 'levels only; the author cannot listen',
    'rows': rows}, indent=2), encoding='utf-8')
for r in rows:
    print('%-16s bedSupp %6.1f dB  meanGain %6.1f dB  unity %5.1f%%  rms %+.2f'
          % (r['clip'], r['bed_suppression_db'], r['mean_gain_on_music_db'],
             r['unity_pct'], r['rms_delta_db']))
print('pack ->', PACK)
print('editor running:',
      bool(__import__('subprocess').run(
          ['powershell', '-NoProfile', '-Command',
           "(Get-Process UnrealEditor -ErrorAction SilentlyContinue | Measure-Object).Count"],
          capture_output=True, text=True).stdout.strip()))