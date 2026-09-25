"""Author the DW715 Eject and Close wind fix: raise the high-pass to 800 Hz.

Why this and not a rebuild: the mechanism occupies 1.5-8 kHz while the wind sits
at 250-1000 Hz, so the delivered 200 Hz high-pass left the wind almost entirely
inside the passband.  Raising it to 800 Hz removes 18-19 dB of wind while the
mechanism peak is unchanged (measured -29.3 dBFS before and after, both clips).
The recording itself is kept -- this is a filter change, not a rebuild.

Outputs to `rebuild/`; nothing is installed into Content by this script.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild'
OUT.mkdir(exist_ok=True)
SR = 48000
HIGHPASS_HZ = 800
FILTER_ORDER = 4
FADE_ATTACK_S, FADE_RELEASE_S = .003, .018

# same windows the delivered assets were cut from, unchanged
WINDOWS = {
    'Eject': (1.800, 2.230, .46),
    'Close': (4.940, 5.420, .58),
}

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
assert sr == SR, sr


def dbfs(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


def bp(x, lo, hi):
    s = signal.butter(3, [lo, hi], fs=SR, btype='bandpass', output='sos')
    return signal.sosfiltfilt(s, x, axis=0)


def fade(x):
    y = np.asarray(x).copy()
    n = min(round(SR * FADE_ATTACK_S), len(y) // 2)
    m = min(round(SR * FADE_RELEASE_S), len(y) // 2)
    y[:n] *= np.sin(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    y[-m:] *= np.cos(np.linspace(0, np.pi / 2, m))[:, None] ** 2
    return y


rows = []
for name, (a, b, peak_target) in WINDOWS.items():
    seg = raw[round(a * SR):round(b * SR)]
    sos = signal.butter(FILTER_ORDER, HIGHPASS_HZ, fs=SR, btype='highpass', output='sos')
    y = signal.sosfiltfilt(sos, seg, axis=0)
    # keep the delivered asset's own peak level so the cue balance in game is untouched
    y = y * (peak_target / max(float(np.max(np.abs(y))), 1e-12))
    clip = fade(y)

    old, _ = sf.read(HERE / ('Waves/S_DW715_Loader_%s.wav' % name))
    old = np.asarray(old)
    path = OUT / ('S_DW715_Loader_%s_rebuilt.wav' % name)
    sf.write(path, clip, SR, subtype='PCM_16')

    def wind(x):
        return dbfs(bp(x, 250, 1000))

    def mech(x):
        return round(float(20 * np.log10(np.max(np.abs(bp(x, 1500, 8000))) + 1e-12)), 1)

    def share(x):
        return round(100 * float(np.sum(bp(x, 250, 1000) ** 2) / max(np.sum(x ** 2), 1e-30)), 2)

    rows.append({
        'clip': name,
        'span_s': [a, b],
        'duration_ms': round(len(clip) / SR * 1000, 1),
        'highpass_hz': HIGHPASS_HZ,
        'peak_before': round(float(np.max(np.abs(old))), 4),
        'peak_after': round(float(np.max(np.abs(clip))), 4),
        'rms_before_dbfs': dbfs(old), 'rms_after_dbfs': dbfs(clip),
        'wind_band_before_dbfs': wind(old), 'wind_band_after_dbfs': wind(clip),
        'wind_reduction_db': round(wind(old) - wind(clip), 1),
        'mech_peak_before_dbfs': mech(old), 'mech_peak_after_dbfs': mech(clip),
        'wind_share_before_pct': share(old), 'wind_share_after_pct': share(clip),
        'samples': len(clip),
    })
    print(json.dumps(rows[-1], ensure_ascii=False))

(OUT / 'rebuild_report.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False),
                                         encoding='utf-8')
print()
for p in sorted(OUT.glob('*.wav')):
    print(p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()[:16])