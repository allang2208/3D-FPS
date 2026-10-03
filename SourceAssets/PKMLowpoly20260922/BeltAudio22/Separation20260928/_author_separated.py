"""Re-author all PKM reload contact cues from a separated (de-BGM'ed) track,
replicating the original authoring chains exactly:
  BeltAudio22: 80 Hz HP -> cut -> atempo -> 3/25 ms fades -> one common gain.
  ChargeAudio35: same, plus per-cue trim_lead.
Source track is mono 48 kHz built from chosen Demucs stems.
"""
from pathlib import Path
import argparse
import json
import subprocess
import tempfile

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, resample_poly

HERE = Path(__file__).resolve().parent
RATE = 48000

BELT_CUES = [
    ('CoverOpen', 10.825, 11.340, .72),
    ('BeltLift', 11.745, 12.185, .74),
    ('BoxOut', 12.420, 12.900, 1.),
    ('BoxInsert', 14.245, 14.470, 1.),
    ('BeltSeat', 15.230, 15.435, 1.),
    ('CoverClose', 15.865, 16.100, 1.),
]
CHARGE_CUES = [
    ('ChargePullMove', 24.180, 24.710, 2.3043478260869614, .0),
    ('ChargeRearStop', 24.710, 24.905, 1., .003),
    ('ChargePushMove', 24.905, 25.010, 0.30882352941176594, .0),
    ('ChargeFrontStop', 25.010, 25.225, 1., .003),
]


def build_source(combo):
    orig, r = sf.read(HERE / 'ref_stereo48.wav', always_2d=True)
    assert r == RATE
    def stem(model_dir, name):
        x, sr = sf.read(HERE / model_dir / 'ref_stereo48' / f'{name}.wav', always_2d=True)
        if sr != RATE:
            g = np.gcd(RATE, sr)
            x = resample_poly(x, RATE // g, sr // g, axis=0)
        return x
    if combo == 'orig':
        return orig.mean(axis=1)
    if combo.startswith('4/'):
        s = {'bass': stem('sep4/htdemucs', 'bass'), 'drums': stem('sep4/htdemucs', 'drums'),
             'other': stem('sep4/htdemucs', 'other'), 'vocals': stem('sep4/htdemucs', 'vocals')}
        if combo == '4/orig_minus_bass':
            y = orig - s['bass']
        elif combo == '4/orig_minus_bass_vocals':
            y = orig - s['bass'] - s['vocals']
        elif combo == '4/drums_plus_other':
            y = s['drums'] + s['other']
        else:
            raise SystemExit(f'unknown combo {combo}')
        return y.mean(axis=1)
    if combo.startswith('6/'):
        s = {n: stem('sep6/htdemucs_6s', n) for n in ('bass', 'drums', 'other', 'vocals', 'piano', 'guitar')}
        music = s['bass'] + s['piano'] + s['guitar'] + s['vocals']
        if combo == '6/orig_minus_tonal':
            y = orig - music
        elif combo == '6/orig_minus_tonal_drums':
            y = orig - music - s['drums']
        elif combo == '6/other_only':
            y = s['other']
        elif combo == '6/other_plus_drums':
            y = s['other'] + s['drums']
        else:
            raise SystemExit(f'unknown combo {combo}')
        return y.mean(axis=1)
    raise SystemExit(f'unknown combo {combo}')


def author(x, cues, out_dir, hp=80.):
    x = sosfiltfilt(butter(2, hp, fs=RATE, btype='highpass', output='sos'), x)
    clips = []
    with tempfile.TemporaryDirectory(prefix='pkm_sep_') as temp:
        for cue in cues:
            name, start, end, tempo = cue[0], cue[1], cue[2], cue[3]
            trim_lead = cue[4] if len(cue) > 4 else 0.
            y = x[round((start + trim_lead) * RATE):round(end * RATE)].copy()
            if tempo != 1.:
                iw, ow = Path(temp) / 'in.wav', Path(temp) / 'out.wav'
                sf.write(iw, y, RATE, subtype='FLOAT')
                subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error',
                                '-i', str(iw), '-af', f'atempo={tempo}', '-c:a', 'pcm_f32le',
                                str(ow)], check=True)
                y, _ = sf.read(ow)
            attack, release = round(.003 * RATE), round(.025 * RATE)
            y[:attack] *= np.linspace(0., 1., attack)
            y[-release:] *= np.linspace(1., 0., release)
            clips.append((name, y))
    peak = max(float(np.max(np.abs(c[1]))) for c in clips)
    gain = 10 ** (-2. / 20.) / peak
    manifest = []
    for name, y in clips:
        wav = out_dir / f'S_PKM_{name}.wav'
        sf.write(wav, y * gain, RATE, subtype='PCM_16')
        manifest.append({'name': name, 'wav': wav.name, 'duration': round(len(y) / RATE, 6),
                         'peak_dbfs': round(float(20 * np.log10(np.max(np.abs(y * gain)))), 3)})
    return {'common_gain_db': round(float(20 * np.log10(gain)), 4), 'contacts': manifest}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('combo')
    args = ap.parse_args()
    src = build_source(args.combo)
    out = HERE / 'candidates' / args.combo.replace('/', '_')
    (out / 'BeltAudio22').mkdir(parents=True, exist_ok=True)
    (out / 'ChargeAudio35').mkdir(parents=True, exist_ok=True)
    rep = {'combo': args.combo,
           'belt': author(src, BELT_CUES, out / 'BeltAudio22'),
           'charge': author(src, CHARGE_CUES, out / 'ChargeAudio35')}
    (out / 'manifest.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
