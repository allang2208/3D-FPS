"""CoverOpen / CoverClose: the 2026-09-25 accepted build vs the 2026-09-28 v2 build.

The user accepted the 09-25 covers by ear, and the v2 round replaced them with a
different recipe.  Both are kept side by side here so the choice is theirs, with
the raw cut included as the "with BGM" reference.

Per cover, peak-aligned and looped:
  A_*_RAW_withBGM.wav     the untouched video cut -- what the bed sounds like
  B_*_20260925.wav        the 09-25 rebuild the user accepted
  C_*_20260928_v2.wav     the v2 rebuild
  D_*_tail_20260925.wav   the replaced tail alone, 09-25 recipe
  E_*_tail_v2.wav         the replacement tail alone, v2 recipe

Nothing is imported or changed on disk here; this only writes a listening pack.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
OLD = PARENT / 'rebuild'
NEW = HERE / 'out2'
PACK = HERE / 'out2' / '_covers_ab'
PACK.mkdir(parents=True, exist_ok=True)
RATE = 48000

COVERS = ['CoverOpen', 'CoverClose']
REPORT = {r['clip']: r for r in json.loads(
    (NEW / 'debgm2_report.json').read_text(encoding='utf-8'))['rows']}


def rd(p):
    return np.asarray(sf.read(p)[0], dtype=np.float64)


def align(v, tgt):
    p = float(np.max(np.abs(v)))
    return v * (tgt / p) if p > 0 else v


def rms_db(v):
    return round(20 * float(np.log10(np.sqrt(np.mean(v ** 2)) + 1e-30)), 2)


rows = []
for name in COVERS:
    raw = rd(PARENT / f'S_PKM_{name}.wav')
    v925 = rd(OLD / f'S_PKM_{name}_rebuilt_delivered.wav')
    v2 = rd(NEW / f'S_PKM_{name}_debgm2.wav')
    ho = int(REPORT[name]['handover_sample'])
    tail_925 = v925[ho:]
    tail_v2 = rd(NEW / f'_{name}_tail_NEW.wav')
    assert len(v925) == len(raw) == len(v2), 'length mismatch for %s' % name

    pk = float(np.max(np.abs(raw)))
    for tag, v, loops in (('A', raw, 3), ('B', v925, 3), ('C', v2, 3)):
        sf.write(PACK / f'{tag}_{name}_{ {"A": "RAW_withBGM", "B": "20260925", "C": "20260928_v2"}[tag] }.wav',
                 np.tile(align(v, pk), loops), RATE, subtype='PCM_16')

    tp = max(float(np.max(np.abs(tail_925))), float(np.max(np.abs(tail_v2))), 1e-9)
    sf.write(PACK / f'D_{name}_tail_20260925.wav', np.tile(align(tail_925, tp), 4),
             RATE, subtype='PCM_16')
    sf.write(PACK / f'E_{name}_tail_v2.wav', np.tile(align(tail_v2, tp), 4),
             RATE, subtype='PCM_16')

    rows.append({'cover': name, 'samples': len(raw),
                 'raw_peak_db': round(20 * np.log10(pk), 2),
                 'raw_rms_db': rms_db(raw),
                 'v925_rms_db': rms_db(v925), 'v2_rms_db': rms_db(v2),
                 'v925_vs_raw_db': round(rms_db(v925) - rms_db(raw), 2),
                 'v2_vs_raw_db': round(rms_db(v2) - rms_db(raw), 2),
                 'v925_vs_v2_db': round(rms_db(v925) - rms_db(v2), 2),
                 'first_diff_sample_v925_vs_v2': int(np.argmax(v925 != v2))
                 if np.any(v925 != v2) else None,
                 'handover_sample': ho})

(PACK / 'README.json').write_text(json.dumps({
    'question': 'Which cover build should stay installed?',
    'A': 'untouched video cut (with BGM) -- the reference for what the bed sounds like',
    'B': 'the 2026-09-25 rebuild the user accepted',
    'C': 'the 2026-09-28 v2 rebuild, now installed',
    'D_E': 'the replaced tail alone (09-25) vs the replacement tail alone (v2), 4 loops',
    'installed_now': 'C (v2) is what is currently in Content',
    'author_note': 'No listening was performed by the author; levels only.', 'rows': rows},
    indent=2), encoding='utf-8')
for r in rows:
    print(json.dumps(r))
print('\npack ->', PACK)