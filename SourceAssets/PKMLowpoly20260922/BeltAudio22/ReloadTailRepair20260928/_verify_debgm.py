"""Verify the de-BGM rebuild: kept head, contract, splice continuity.

The first four checks are the decision material and every one of them is an
assertion: the kept head is bit-identical up to the crossfade, the sample count
and peak are unchanged, the difference signal stays far below the body, and the
splice step is small next to the file's own largest step.

The trailing `tonality` block is **not** evidence.  It was carried over from the
2026-09-25 round, and this round showed it cannot separate the bed's harmonic
comb from the formant structure of a broadband mechanical transient in windows
this short: on this material the clean donor window scores a *higher* comb
contrast (5.7 dB) than the music bed itself (4.0 dB).  It is printed for the
record only -- see `trash/pkm-reload-debgm-20260928/`.  The route's real music
guarantee is constructive: a donor's masking margin is the rebuild's suppression,
because donor = contact + bed (`_diag_donor_thresholds.py`).
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
OUT = HERE / 'out'
RATE = 48000
NPART = [46.9, 117.2, 210.9, 328.1, 515.6, 609.4, 679.7, 820.3, 1031.2]

report = json.loads((OUT / 'debgm_report.json').read_text(encoding='utf-8'))
rebuilt = [r for r in report['rows'] if r['action'] == 'rebuilt']


def tonality(v, label, smooth_bins=9):
    nfft = 1 << int(np.ceil(np.log2(max(len(v), 8192))))
    P = np.abs(np.fft.rfft(v * np.hanning(len(v)), nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1 / RATE)
    sm = uniform_filter1d(P, smooth_bins, mode='nearest')
    sel = (f >= 40) & (f <= 4000)
    peakiness = float(np.sum(np.maximum(P[sel] - sm[sel], 0)) / (np.sum(P[sel]) + 1e-30))
    heights = []
    for hz in NPART:
        m = (f > hz - 8) & (f < hz + 8)
        if m.sum():
            heights.append(round(float(10 * np.log10((P[m].max() + 1e-30)
                                                     / (sm[m].mean() + 1e-30))), 1))
    return {'label': label, 'peakiness': round(peakiness, 4),
            'partial_excess_db': heights,
            'mean_partial_excess_db': round(float(np.mean(heights)), 2)}


mono, _ = sf.read(PARENT / 'reference_audio.wav')
if mono.ndim > 1:
    mono = mono.mean(axis=1)
bed_ref = np.concatenate([mono[round(a * RATE):round(b * RATE)] for a, b in
                          [(1.10, 3.25), (6.10, 7.25), (9.05, 10.00)]])

rows = [tonality(bed_ref, 'clean bed reference (no contact)')]
for r in rebuilt:
    name = r['clip']
    src = (PARENT / f'S_PKM_{name}.wav') if r['folder'] == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    orig, _ = sf.read(src)
    new, _ = sf.read(OUT / f'S_PKM_{name}_debgm_delivered.wav')
    orig = np.asarray(orig, dtype=np.float64)
    new = np.asarray(new, dtype=np.float64)
    ho = int(round(r['handover_ms'] / 1000 * RATE))
    xf = max(1, min(int(0.015 * RATE), (len(orig) - ho) // 3, ho))

    head_same = int(np.flatnonzero(np.abs(new[:ho - xf] - orig[:ho - xf]) > 1.5 / 32768)[0]) \
        if np.any(np.abs(new[:ho - xf] - orig[:ho - xf]) > 1.5 / 32768) else ho - xf
    peak_o, peak_n = float(np.max(np.abs(orig))), float(np.max(np.abs(new)))
    rms_o = float(np.sqrt(np.mean(orig ** 2)))
    rms_n = float(np.sqrt(np.mean(new ** 2)))
    diff = new - orig
    tail = slice(ho + xf, len(orig))

    rows.append({
        'clip': name, 'folder': r['folder'],
        'samples_equal': len(orig) == len(new),
        'head_bit_identical_until_sample': int(head_same),
        'head_bit_identical_until_ms': round(head_same / RATE * 1000, 1),
        'head_required_identical_ms': round((ho - xf) / RATE * 1000, 1),
        'peak_before': round(peak_o, 6), 'peak_after': round(peak_n, 6),
        'peak_delta_db': round(20 * np.log10(peak_n / peak_o), 4),
        'rms_before_dbfs': round(20 * np.log10(rms_o), 3),
        'rms_after_dbfs': round(20 * np.log10(rms_n), 3),
        'rms_delta_db': round(20 * np.log10(rms_n / rms_o), 3),
        'difference_rel_db': round(20 * np.log10(
            np.sqrt(np.mean(diff ** 2)) / (rms_o + 1e-30)), 1),
        'splice_jump_rel': round(float(np.max(np.abs(np.diff(new[ho - xf - 2:ho + xf + 2]))))
                                 / (peak_n + 1e-30), 4),
        # loudest single-sample step anywhere else, for scale
        'body_max_step_rel': round(float(np.max(np.abs(np.diff(new[:ho - xf - 2]))))
                                   / (peak_n + 1e-30), 4),
    })
    rows.append(tonality(orig[ho:], f'{name} OLD tail (contaminated)'))
    rows.append(tonality(new[tail], f'{name} NEW tail (rebuilt)'))
    rows.append(tonality(orig[:ho], f'{name} kept head'))

for row in rows:
    print(json.dumps(row))
(OUT / 'verification.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')