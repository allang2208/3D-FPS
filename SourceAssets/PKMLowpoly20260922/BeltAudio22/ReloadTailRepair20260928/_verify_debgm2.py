"""Verify the second-generation rebuild, and measure the music in the bed's own band.

Loudness is not the question -- the bed is a low-mid hum, so the honest metric is
how much energy the rebuilt tail carries *in the band the bed actually lives in*
(250-1000 Hz, where 78 % of the reload bed and 90 % of the charge bed sits).
Reporting broadband RMS would hide exactly the failure the first attempt had: it
level-matched the tail to the bed, so it read "quiet enough" overall while being
a resynthesis of the bed.

Assertions:
  * kept region bit-identical up to the crossfade
  * sample count and peak unchanged
  * splice step small next to the file's own largest step
  * bed-band energy in the tail is strictly lower than before, never higher
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
OUT = HERE / 'out2'
RATE, NP, HOP = 48000, 2048, 512
BED_BAND = (250, 1000)

report = json.loads((OUT / 'debgm2_report.json').read_text(encoding='utf-8'))
FOLDERS = {r['clip']: ('ReloadAudio22' if r['clip'] in
                       ('CoverOpen', 'BeltLift', 'BoxOut', 'BoxInsert', 'BeltSeat', 'CoverClose')
                       else 'ChargeAudio35') for r in report['rows']}

rows, failed = [], []
for r in report['rows']:
    if r['action'] != 'rebuilt':
        rows.append(r)
        continue
    name = r['clip']
    raw = (PARENT / f'S_PKM_{name}.wav') if FOLDERS[name] == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    old = np.asarray(sf.read(raw)[0], dtype=np.float64)
    new = np.asarray(sf.read(OUT / f'S_PKM_{name}_debgm2.wav')[0], dtype=np.float64)
    # exact sample positions, recorded by the author: reconstructing `ho` from the
    # rounded `handover_ms` lands a sample or two off the 512-sample frame grid
    ho = int(r['handover_sample'])
    tail_n = len(old) - ho
    xf = int(r['crossfade_samples'])

    def band_power(v):
        # the shortest tails are ~9 ms (430 samples): clamp the window and its
        # overlap together, or stft rejects noverlap >= nperseg
        nper = int(min(NP, len(v)))
        nper = max(64, 1 << int(np.floor(np.log2(nper))))
        _, _, Z = stft(v, fs=RATE, nperseg=nper, noverlap=nper // 4, window='hann',
                       boundary='zeros', padded=True)
        f = np.fft.rfftfreq(nper, 1 / RATE)
        sel = (f >= BED_BAND[0]) & (f < BED_BAND[1])
        return float(np.mean(np.abs(Z[sel]) ** 2))

    o_tail, n_tail = old[ho:], new[ho + xf:]
    bp_old, bp_new = band_power(o_tail), band_power(n_tail)
    head_ok = int(np.argmax(new[:ho + xf] != old[:ho + xf])) if np.any(
        new[:ho + xf] != old[:ho + xf]) else ho + xf
    body_step = float(np.max(np.abs(np.diff(old[:ho])))) if ho > 1 else 0.0
    splice = abs(float(new[ho]) - float(old[ho - 1]))

    row = dict(r)
    row.update({
        'head_bit_identical_until_ms': round(head_ok / RATE * 1000, 1),
        'head_required_identical_ms': round(max(0, ho - xf) / RATE * 1000, 1),
        'head_first_diff_sample': head_ok,
        'crossfade_start_sample': ho - xf,
        'head_ok': bool(head_ok >= ho - xf),
        'samples_equal': len(new) == len(old),
        'peak_delta_db': round(20 * np.log10((float(np.max(np.abs(new))) + 1e-30) /
                                             (float(np.max(np.abs(old))) + 1e-30)), 3),
        'bed_band_hz': list(BED_BAND),
        'bed_band_old_tail_db': round(10 * np.log10(bp_old + 1e-30), 1),
        'bed_band_new_tail_db': round(10 * np.log10(bp_new + 1e-30), 1),
        'bed_band_suppression_db': round(10 * np.log10(bp_old + 1e-30) - 10 * np.log10(bp_new + 1e-30), 1),
        'splice_step': round(splice, 6),
        'body_max_step': round(body_step, 6),
        'splice_below_body_step': bool(splice <= body_step),
    })
    if not row['samples_equal'] or abs(row['peak_delta_db']) > 1e-3:
        failed.append('%s contract' % name)
    # compare in samples: inside the crossfade the first few samples can
    # coincidentally round back to the same PCM16 value, so the first *differing*
    # sample may legitimately sit a few samples after the crossfade start
    if not row['head_ok']:
        failed.append('%s kept-head not bit-identical' % name)
    if not row['splice_below_body_step']:
        failed.append('%s splice step' % name)
    if row['bed_band_suppression_db'] < 0:
        failed.append('%s bed band got louder' % name)
    rows.append(row)
    print(json.dumps({k: row[k] for k in (
        'clip', 'rebuilt_ms', 'head_bit_identical_until_ms', 'head_required_identical_ms',
        'samples_equal', 'peak_delta_db', 'bed_band_old_tail_db', 'bed_band_new_tail_db',
        'bed_band_suppression_db', 'splice_step', 'body_max_step')}))

(OUT / 'verification2.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('\n=== bed-band (250-1000 Hz) suppression in each rebuilt tail ===')
for r in rows:
    if r.get('bed_band_suppression_db') is not None:
        print('  %-16s %+6.1f dB   (%.1f -> %.1f dB in band)'
              % (r['clip'], r['bed_band_suppression_db'],
                 r['bed_band_old_tail_db'], r['bed_band_new_tail_db']))
print('\nchecks failed: %s' % (failed if failed else 'none'))