"""Diagnostic only: splice safety and decay naturalness of the rebuilt tails."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild'
RATE = 48000

PLAN = [('CoverOpen', 437.3 / 1000, .72), ('CoverClose', 192.0 / 1000, 1.0)]
rows = []
for name, ho_s, tempo in PLAN:
    raw, _ = sf.read(OUT / f'S_PKM_{name}_rebuilt_raw.wav')
    raw = np.asarray(raw)
    ho = int(round(ho_s * RATE))
    # discontinuity across the splice vs the surrounding signal's own roughness
    d = np.diff(raw)
    local = np.abs(d[max(0, ho - 300):ho + 300])
    step = abs(raw[ho] - raw[ho - 1])
    rows.append({
        'clip': name,
        'splice_sample_step': round(float(step), 6),
        'local_max_abs_diff': round(float(local.max()), 6),
        'local_mean_abs_diff': round(float(local.mean()), 6),
        'step_over_local_max': round(float(step / (local.max() + 1e-12)), 3),
        'global_max_abs_diff': round(float(np.abs(d).max()), 6),
        'splice_step_over_global_max': round(float(step / (np.abs(d).max() + 1e-12)), 3),
    })
    # decay profile of the rebuilt tail
    tail = raw[ho:]
    step_n = max(1, int(0.005 * RATE))
    prof = [round(float(np.sqrt(np.mean(tail[i:i + step_n] ** 2))), 6)
            for i in range(0, len(tail) - step_n, step_n)]
    rows[-1]['new_tail_rms_5ms'] = prof
    rows[-1]['new_tail_decay_db'] = [round(float(20 * np.log10((v + 1e-12) / (prof[0] + 1e-12))), 1)
                                     for v in prof]
    print(json.dumps({k: v for k, v in rows[-1].items()
                      if k not in ('new_tail_rms_5ms',)}))
(OUT / 'splice_check.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

# delivered length vs the original asset, which the game's timing depends on
print('\nlength audit (delivered vs the asset currently in use):')
for name in ('CoverOpen', 'CoverClose'):
    o, _ = sf.read(HERE / f'S_PKM_{name}.wav')
    n, _ = sf.read(OUT / f'S_PKM_{name}_rebuilt_delivered.wav')
    o, n = np.asarray(o), np.asarray(n)
    print(f'  {name}: original {len(o)} samp ({len(o)/RATE*1000:.2f} ms) | '
          f'rebuilt {len(n)} samp ({len(n)/RATE*1000:.2f} ms) | '
          f'delta {len(n)-len(o)} samp ({(len(n)-len(o))/RATE*1000:+.2f} ms)')