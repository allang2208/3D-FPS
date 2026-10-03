"""Quick BGM separability pre-screen for any candidate reload-sound video.

Answers one question before any authoring work: can mechanical contact sounds
be cut from this video without music bleeding in?

Usage:
  python check_source_bgm.py <video_or_audio> [--windows 10.8-11.3,24.2-25.2]

Prints a 2 s-resolution bed-activity map (bed-band 250-1000 Hz level plus
harmonic-comb fingerprint) and, for each requested window, a verdict:
  CLEAN      no detectable music bed in the window
  GATED      bed present but >=35 dB below the track's transient reference
  USABLE     bed quiescent or faint in most of the window (cuts need care)
  REJECT     bed active and loud enough to survive impacts (like the 2026-09-22
             PKM reference: continuous harmonic bed, ~22 dB under impacts)

Verdict thresholds come from the 2026-09-25/28 PKM BGM findings: 22 dB of
masking during impacts was NOT enough; every cue had 23-74% exposed frames.
"""
from pathlib import Path
import argparse
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, resample_poly

RATE = 48000
BED = (250., 1000.)
HARMONICS = [46.9, 117.2, 210.9, 328.1, 515.6, 609.4, 679.7, 820.3]
STEP = 2.0  # seconds per map row


def decode(path):
    path = Path(path)
    if path.suffix.lower() == '.wav':
        x, r = sf.read(path, always_2d=True)
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'a.wav'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error',
                            '-i', str(path), '-vn', '-ar', str(RATE), '-ac', '1',
                            '-c:a', 'pcm_s24le', str(out)], check=True)
            x, r = sf.read(out, always_2d=True)
    x = x.mean(axis=1)  # flatten any (N,1)/(N,2) into mono
    if r != RATE:
        g = np.gcd(RATE, r)
        x = resample_poly(x, RATE // g, r // g)
    return x.astype(np.float64)


def band(x, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], fs=RATE, btype='bandpass', output='sos'), x)


def harmonic_comb_db(seg):
    """Mean spectrum excess at the PKM bed's harmonic slivers vs sidebands."""
    n = len(seg)
    if n < 4096:
        return 0.
    spec = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2
    res = RATE / n
    on, off = [], []
    w = max(1, int(round(2.0 / res)))
    for h in HARMONICS:
        i = int(round(h / res))
        lo, hi = max(0, i - w), min(len(spec), i + w + 1)
        if hi <= lo:
            continue
        on.append(spec[lo:hi].mean())
        for c in (h - 8., h + 8.):
            j = int(round(c / res))
            a, b = max(0, j - w), min(len(spec), j + w + 1)
            if b > a:
                off.append(spec[a:b].mean())
    if not on or not off:
        return 0.
    return float(10 * np.log10(np.mean(on) / max(np.mean(off), 1e-20)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--windows', help='comma list of start-end seconds to judge, e.g. 10.8-11.3,24.2-25.2')
    args = ap.parse_args()

    x = decode(args.source)
    dur = len(x) / RATE
    bed = band(x, *BED)

    # Transient reference: 95th percentile of 10 ms broadband peak levels.
    k = int(.01 * RATE)
    peaks = np.array([np.max(np.abs(x[i:i + k])) for i in range(0, len(x) - k, k)])
    ref = float(np.percentile(peaks, 95))
    ref_db = 20 * np.log10(ref + 1e-12)

    rows = []
    nstep = int(STEP * RATE)
    print(f'duration {dur:.2f}s   transient reference p95 {ref_db:.1f} dBFS')
    print(f'{"window":>10s} {"bed dBFS":>9s} {"comb dB":>8s}  activity')
    for i in range(0, len(x) - nstep, nstep):
        s = x[i:i + nstep]
        b = bed[i:i + nstep]
        rms = float(np.sqrt(np.mean(b ** 2)))
        comb = harmonic_comb_db(s)
        rel = 20 * np.log10(rms + 1e-12) - ref_db
        act = 'ACTIVE' if (comb > 1.0 and rel > -40) else ('faint' if rel > -50 else 'quiet')
        rows.append((i / RATE, rms, comb, act))
        print(f'{i / RATE:8.1f}s {20 * np.log10(rms + 1e-12):9.1f} {comb:8.1f}  {act}')

    if args.windows:
        print()
        for w in args.windows.split(','):
            a, b = (float(v) for v in w.split('-'))
            s = x[int(a * RATE):int(b * RATE)]
            bs = bed[int(a * RATE):int(b * RATE)]
            if len(s) < 1:
                continue
            comb = harmonic_comb_db(s)
            # Window-local transient reference: friction-heavy cues are far
            # quieter than the track-wide p95, and the bed must be judged
            # against what actually masks it inside this window.
            kw = int(.01 * RATE)
            wpeaks = np.array([np.max(np.abs(s[i:i + kw])) for i in range(0, len(s) - kw, kw)]) if len(s) > kw else np.abs(s)
            wref = float(np.percentile(wpeaks, 95)) + 1e-12
            # per-100ms frames: bed level vs window-local transient reference
            kf = int(.1 * RATE)
            rels = [20 * np.log10(np.sqrt(np.mean(bs[i:i + kf] ** 2)) + 1e-12) - 20 * np.log10(wref)
                    for i in range(0, len(bs) - kf, kf)]
            rels = np.array(rels)
            exposed = float(np.mean((rels > -35) & (comb > 0.))) * 100
            worst = float(np.max(rels)) if len(rels) else -99.
            if comb <= 0.5 and worst < -45:
                verdict = 'CLEAN'
            elif worst < -35:
                verdict = 'GATED (bed >=35 dB under transients)'
            elif exposed < 30:
                verdict = 'USABLE (bed quiescent in most frames)'
            else:
                verdict = 'REJECT (bed active, like the 09-22 PKM reference)'
            print(f'window {a:.2f}-{b:.2f}s  comb {comb:+.1f} dB  worst-bed-vs-ref {worst:+.1f} dB  '
                  f'exposed {exposed:.0f}%  -> {verdict}')


if __name__ == '__main__':
    main()
