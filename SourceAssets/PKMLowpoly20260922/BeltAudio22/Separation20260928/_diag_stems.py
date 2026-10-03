"""Quantify each Demucs stem and candidate SFX combos against the project's own
acceptance yardsticks: bed-band (250-1000 Hz) suppression per cue window and
mechanical transient preservation (peak level/position, first-30 ms energy).

Bed fingerprint harmonics from BGM_FINDINGS.md: 46.9/117.2/210.9/328.1/515.6/
609.4/679.7/820.3 Hz. Cue windows from audio_manifest.json (BeltAudio22) and
ChargeAudio35/audio_manifest.json.
"""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, resample_poly

HERE = Path(__file__).resolve().parent
RATE = 48000
BED = (250., 1000.)
HARMONICS = [46.9, 117.2, 210.9, 328.1, 515.6, 609.4, 679.7, 820.3]

CUES = [
    # name, video_start, video_end (seconds, source-video clock)
    ('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
    ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
    ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100),
    ('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
    ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225),
]
# Quiet windows: bed-only exposure (no contacts) for stem fingerprinting.
QUIET = [('Q1', 9.05, 10.00), ('Q2', 17.5, 18.6), ('Q3', 21.0, 22.2), ('Q4', 30.0, 31.5)]


def load(path):
    x, r = sf.read(path, always_2d=True)
    if r != RATE:
        g = np.gcd(RATE, r)
        x = resample_poly(x, RATE // g, r // g, axis=0)
    return x.mean(axis=1)  # mono, matches authoring chain


def band_rms(x, lo, hi):
    sos = butter(4, [lo, hi], fs=RATE, btype='bandpass', output='sos')
    y = sosfiltfilt(sos, x)
    return float(np.sqrt(np.mean(y ** 2))), y


def harmonic_excess(x):
    """Mean energy in +-2 Hz slivers around bed harmonics vs surrounding bands."""
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    freqs = np.fft.rfftfreq(n, 1. / RATE)
    res = RATE / n  # frequency resolution
    on, off = [], []
    for h in HARMONICS:
        i = int(round(h / res))
        w = max(1, int(round(2.0 / res)))
        lo, hi = max(0, i - w), min(len(spec), i + w + 1)
        if hi <= lo:
            continue
        on.append(spec[lo:hi].mean())
        for center in (h - 8., h + 8.):
            j = int(round(center / res))
            a, b = max(0, j - w), min(len(spec), j + w + 1)
            if b > a:
                off.append(spec[a:b].mean())
    if not on or not off:
        return 0.
    return float(10 * np.log10(np.mean(on) / max(np.mean(off), 1e-20)))


def window(x, a, b, pad=0.05):
    return x[int((a - pad) * RATE):int((b + pad) * RATE)]


def cue_metrics(orig, cand, a, b):
    """Bed-band suppression (dB) + transient preservation for one cue window."""
    o = window(orig, a, b)
    c = window(cand, a, b)
    n = min(len(o), len(c))
    o, c = o[:n], c[:n]
    ob_rms, _ = band_rms(o, *BED)
    cb_rms, _ = band_rms(c, *BED)
    supp = float(20 * np.log10(ob_rms / max(cb_rms, 1e-12)))
    # Transient: strongest broadband peak in the original, track it in candidate.
    op, cp = int(np.argmax(np.abs(o))), int(np.argmax(np.abs(c)))
    pk_keep = float(20 * np.log10(max(np.abs(c)) / max(np.abs(o))))
    # First-30 ms energy after the original's peak, both aligned at that peak.
    k = min(int(.03 * RATE), n - op)
    o30 = float(np.sqrt(np.mean(o[op:op + k] ** 2)))
    c30 = float(np.sqrt(np.mean(c[op:op + k] ** 2)))
    e30 = float(20 * np.log10(max(c30, 1e-12) / max(o30, 1e-12)))
    return {'bed_suppression_db': round(supp, 1), 'peak_keep_db': round(pk_keep, 2),
            'peak_sample_shift': cp - op, 'first30ms_keep_db': round(e30, 1)}


def main():
    orig = load(HERE / 'ref_stereo48.wav')
    stems4 = {p.stem: load(p) for p in sorted((HERE / 'sep4/htdemucs/ref_stereo48').glob('*.wav'))}
    stems6 = {p.stem: load(p) for p in sorted((HERE / 'sep6/htdemucs_6s/ref_stereo48').glob('*.wav'))}

    report = {'stems': {}, 'quiet_fingerprint': {}, 'combos': {}}

    for tag, stems in (('sep4', stems4), ('sep6', stems6)):
        for name, x in stems.items():
            q = {qn: {'rms_dbfs': round(float(20 * np.log10(np.sqrt(np.mean(window(x, a, b) ** 2)) + 1e-12)), 1),
                      'harmonic_excess_db': round(harmonic_excess(window(x, a, b)), 1)}
                 for qn, a, b in QUIET}
            report['stems'][f'{tag}/{name}'] = q

    # Fingerprint the original bed in quiet windows for reference.
    report['quiet_fingerprint']['original'] = {
        qn: {'rms_dbfs': round(float(20 * np.log10(np.sqrt(np.mean(window(orig, a, b) ** 2)) + 1e-12)), 1),
             'harmonic_excess_db': round(harmonic_excess(window(orig, a, b)), 1)} for qn, a, b in QUIET}

    combos = {}
    combos['4/orig_minus_bass'] = orig - stems4.get('bass', 0)
    combos['4/orig_minus_bass_vocals'] = orig - stems4.get('bass', 0) - stems4.get('vocals', 0)
    combos['4/drums_plus_other'] = stems4.get('drums', 0) + stems4.get('other', 0)
    if 'piano' in stems6:
        music6 = stems6['bass'] + stems6['piano'] + stems6['guitar'] + stems6['vocals']
        combos['6/orig_minus_tonal'] = orig - music6
        combos['6/orig_minus_tonal_drums'] = orig - music6 - stems6['drums']
        combos['6/other_only'] = stems6['other']
        combos['6/other_plus_drums'] = stems6['other'] + stems6['drums']

    for cname, cand in combos.items():
        report['combos'][cname] = {n: cue_metrics(orig, cand, a, b) for n, a, b in CUES}

    (HERE / 'stem_report.json').write_text(json.dumps(report, indent=1))
    # Compact console view.
    print('quiet-window stem fingerprint (bed lives where harmonic_excess is high):')
    for k, v in report['stems'].items():
        h = [f"{q['harmonic_excess_db']}" for q in v.values()]
        r = [f"{q['rms_dbfs']}" for q in v.values()]
        print(f'  {k:24s} harm+ {"/".join(h)} dB   rms {"/".join(r)}')
    print('\nper-cue bed suppression / peak_keep / first30ms_keep (dB):')
    for cname, m in report['combos'].items():
        worst = min(v['bed_suppression_db'] for v in m.values())
        line = '  '.join(f"{n[:10]}:{v['bed_suppression_db']}/{v['peak_keep_db']}" for n, v in m.items())
        print(f'  {cname:28s} worst-bed-supp {worst:+.1f}  {line}')


if __name__ == '__main__':
    main()
