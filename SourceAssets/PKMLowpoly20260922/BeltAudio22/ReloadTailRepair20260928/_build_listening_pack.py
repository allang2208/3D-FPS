"""Why the rebuilt tail is music-free by construction, plus the listening pack.

The spectral proxies that the 2026-09-25 round used (peakiness / partial excess)
do **not** separate the bed's harmonic comb from the formant structure of a
broadband mechanical transient in windows this short -- on this material the
clean donor window scores *higher* comb contrast than the music itself, so those
numbers cannot decide anything.  They are retired to
`trash/pkm-reload-debgm-20260928/`.

What can be measured honestly is the donor's own masking margin, because the
rebuild preserves it:

  * the output is the donor slice through a fixed per-band gain (LTI) times a
    25 ms-smoothed envelope, so the contact:music ratio inside the donor is
    carried through band by band and sample by sample;
  * the delivered tails were flagged precisely because the contact had decayed
    to within 6 dB of the bed, i.e. contact:music was about 0-6 dB there.

So the improvement is the difference between those two ratios.  This script
measures the donor margin and writes the back-to-back listening pack, which is
the actual decision material.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
OUT = HERE / 'out'
PACK = OUT / '_listening'
PACK.mkdir(parents=True, exist_ok=True)
RATE = 48000
NP, HOP = 2048, 512
DONOR_SRC = (25.010, 25.215)
OWNED = 6.0

report = json.loads((OUT / 'debgm_report.json').read_text(encoding='utf-8'))
rebuilt = [r for r in report['rows'] if r['action'] == 'rebuilt']

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)


def frames_db(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30)


bed_wins = [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)]
Ps = []
for a, b in bed_wins:
    _, _, Z = stft(mono[round(a * RATE):round(b * RATE)], fs=RATE, nperseg=NP,
                   noverlap=NP - HOP, window='hann', boundary='zeros', padded=True)
    Ps.append(np.abs(Z) ** 2)
bed_db = float(10 * np.log10(np.sum(np.percentile(np.concatenate(Ps, axis=1), 70, axis=1)) + 1e-30))

donor_margin = frames_db(mono[round(DONOR_SRC[0] * RATE):round(DONOR_SRC[1] * RATE)]) - bed_db
donor = {
    'donor_source_window': list(DONOR_SRC),
    'donor_margin_min_db': round(float(donor_margin.min()), 1),
    'donor_margin_median_db': round(float(np.median(donor_margin)), 1),
    'donor_margin_max_db': round(float(donor_margin.max()), 1),
    'donor_pct_frames_owned': round(100 * float((donor_margin >= OWNED).mean()), 1),
    'old_tail_contact_over_music_db': round(OWNED, 1),
    'rebuilt_tail_contact_over_music_db_at_least': round(float(donor_margin.min()), 1),
    'music_suppression_gain_db_at_least': round(float(donor_margin.min()) - OWNED, 1),
}
print(json.dumps(donor, indent=2))


def loop(v, n):
    return np.tile(v, n)


def peak_align(v, target):
    p = np.max(np.abs(v))
    return v * (target / p) if p > 0 else v


items = []
for r in rebuilt:
    name = r['clip']
    src = (PARENT / f'S_PKM_{name}.wav') if r['folder'] == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    orig = np.asarray(sf.read(src)[0], dtype=np.float64)
    new = np.asarray(sf.read(OUT / f'S_PKM_{name}_debgm_delivered.wav')[0], dtype=np.float64)
    ho = int(round(r['handover_ms'] / 1000 * RATE))
    xf = max(1, min(int(0.015 * RATE), (len(orig) - ho) // 3, ho))
    old_tail, new_tail = orig[ho:], new[ho + xf:]
    target = max(np.max(np.abs(orig)), np.max(np.abs(new)))
    sf.write(PACK / f'1_{name}_BEFORE.wav', loop(peak_align(orig, target), 3), RATE, subtype='PCM_16')
    sf.write(PACK / f'2_{name}_AFTER.wav', loop(peak_align(new, target), 3), RATE, subtype='PCM_16')
    sf.write(PACK / f'3_{name}_difference.wav',
             loop(new - orig, 3), RATE, subtype='PCM_16')
    tp = max(np.max(np.abs(old_tail)), np.max(np.abs(new_tail)))
    sf.write(PACK / f'4_{name}_tail_OLD_contaminated.wav',
             loop(peak_align(old_tail, tp), 4), RATE, subtype='PCM_16')
    sf.write(PACK / f'5_{name}_tail_NEW_rebuilt.wav',
             loop(peak_align(new_tail, tp), 4), RATE, subtype='PCM_16')
    items.append({'clip': name, 'kept_ms': round(ho / RATE * 1000, 1),
                  'old_tail_ms': round(len(old_tail) / RATE * 1000, 1),
                  'new_tail_ms': round(len(new_tail) / RATE * 1000, 1)})

manifest = {
    'purpose': 'PKM reload de-BGM: back-to-back listening comparison',
    'how_to_listen': [
        '1 vs 2: peak-aligned before/after, 3 loops each. Judge whether the '
        'music tail is gone and whether the mechanical impact changed.',
        '4 vs 5: the OLD and NEW tail alone, 4 loops each. This is the part that '
        'was replaced; the difference here is exactly what was removed.',
        '3: what was subtracted. If you can still hear music in it, the cut was '
        'in the wrong place.',
    ],
    'note': 'Offline authoring only. No listening was performed by the author.',
    'items': items,
    'donor': donor,
}
(OUT / 'listening_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(OUT / 'donor_margin.json').write_text(json.dumps(donor, indent=2), encoding='utf-8')
print('\npack:', PACK)
for fp in sorted(PACK.glob('*.wav')):
    print(' ', fp.name, fp.stat().st_size)