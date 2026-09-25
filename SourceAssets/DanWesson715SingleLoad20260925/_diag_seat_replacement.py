"""Pick a replacement for the single-round seating click.

Open/Eject/Close go back to the recorded loader one-shots (the version the user
confirmed). Only the per-cartridge seating sound changes. All of these are the
revolver's own samples, so this measures which reads as a cartridge click.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

DW = Path(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson71520260913\Audio')
SR = 48000

CANDS = [
    ('MagSeat  (current seating)', DW / 'S_DW715_MagSeat.wav'),
    ('MagInsert  (candidate)', DW / 'S_DW715_MagInsert.wav'),
    ('MagOut  (cylinder open, in use)', DW / 'S_DW715_MagOut.wav'),
    ('DryClick  (hammer/striker)', DW / 'S_DW715_DryClick.wav'),
    ('ChargeRelease  (cylinder close, in use)', DW / 'S_DW715_ChargeRelease.wav'),
]


def load(p):
    x, sr = sf.read(p, always_2d=True)
    x = x.mean(axis=1) if x.shape[1] > 1 else x[:, 0]
    if sr != SR:
        x = signal.resample_poly(x, SR, sr)
    return x.astype(np.float64)


def analyse(x):
    n = len(x)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    f, P = signal.welch(x, fs=SR, nperseg=min(4096, n), noverlap=min(2048, n // 2))
    cent = float(np.sum(f * P) / max(np.sum(P), 1e-30))

    # attack: how fast the envelope gets from 10% to 90% of its own peak
    env = np.abs(signal.hilbert(x))
    pk = int(np.argmax(env))
    lo, hi = env[pk] * .1, env[pk] * .9
    i10 = int(np.argmax(env >= lo))
    i90 = int(np.argmax(env >= hi))
    attack_ms = round(max(0, i90 - i10) / SR * 1000, 2)

    # energy concentration in the first 30 ms vs the rest
    k = int(.030 * SR)
    front = round(100 * float(np.sum(x[:k] ** 2)) / max(float(np.sum(x ** 2)), 1e-30), 1)

    hf = signal.sosfiltfilt(signal.butter(3, 1500, fs=SR, btype='highpass', output='sos'), x)
    hf_ratio = round(100 * float(np.sum(hf ** 2)) / max(float(np.sum(x ** 2)), 1e-30), 1)
    return {'dur_ms': round(n / SR * 1000, 1),
            'peak_dbfs': round(20 * np.log10(peak + 1e-12), 1),
            'rms_dbfs': round(20 * np.log10(rms + 1e-12), 1),
            'centroid_hz': round(cent), 'attack_ms': attack_ms,
            'energy_first30ms_pct': front, 'hf_above_1500_pct': hf_ratio}


rows = []
print('%-42s%8s%8s%8s%9s%8s%9s%8s'
      % ('', 'dur', 'peak', 'cent', 'attack', 'first30', 'HF>1.5k', 'rms'))
print('%-42s%8s%8s%8s%9s%8s%9s%8s'
      % ('', 'ms', 'dBFS', 'Hz', 'ms', '%', '%', 'dBFS'))
for label, p in CANDS:
    if not p.is_file():
        print('MISSING', label)
        continue
    a = analyse(load(p)); a['name'] = label
    rows.append(a)
    print('%-42s%8.1f%8.1f%8d%9.2f%8.1f%9.1f%8.1f'
          % (label, a['dur_ms'], a['peak_dbfs'], a['centroid_hz'], a['attack_ms'],
             a['energy_first30ms_pct'], a['hf_above_1500_pct'], a['rms_dbfs']))

out = Path(__file__).resolve().parent
(out / 'seat_replacement.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False),
                                           encoding='utf-8')