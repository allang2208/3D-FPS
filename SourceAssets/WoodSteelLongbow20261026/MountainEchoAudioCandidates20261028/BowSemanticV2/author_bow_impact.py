"""User-directed softer bow-semantic revision of TannerSound candidate B.

Audition only. No UE import or runtime bindings are changed.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly, resample, lfilter

OUT = Path(__file__).resolve().parent
SOURCES = OUT.parent / 'Sources'
ARROWS = Path('D:/FPS3D/FPSGAME/SourceAssets/HeartPiercingArrowAudioCandidates20261026/Sources')
SR = 48000


def read(path, start, end, speed=1.):
    audio, rate = sf.read(path, dtype='float64', always_2d=True)
    audio = audio[round(start*rate):round(end*rate)]
    if rate != SR:
        from math import gcd
        d = gcd(rate, SR)
        audio = resample_poly(audio, SR//d, rate//d, axis=0)
    if speed != 1:
        audio = resample(audio, round(len(audio)/speed), axis=0)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    return audio[:, :2]


def filt(audio, cutoff, kind, order=3):
    return sosfilt(butter(order, cutoff, btype=kind, fs=SR, output='sos'), audio, axis=0)


def bell(audio, hz, gain_db, q):
    a = 10**(gain_db/40)
    omega = 2*np.pi*hz/SR
    alpha = np.sin(omega)/(2*q)
    c = np.cos(omega)
    b = np.array([1+alpha*a, -2*c, 1-alpha*a])
    den = np.array([1+alpha/a, -2*c, 1-alpha/a])
    return lfilter(b/den[0], den/den[0], audio, axis=0)


def edge(audio, attack=.0015, release=.028):
    audio = audio.copy()
    n = min(round(attack*SR), len(audio)//2)
    r = min(round(release*SR), len(audio)//2)
    audio[:n] *= np.linspace(0, 1, n)[:, None]
    audio[-r:] *= np.linspace(1, 0, r)[:, None]
    return audio


def peak(audio):
    return audio / max(1e-8, float(np.abs(audio).max()))


def mix_at(target, audio, start, gain):
    start = round(start*SR)
    length = min(len(audio), len(target)-start)
    target[start:start+length] += audio[:length]*gain


def main():
    # Preserve the first impact, excluding the next strong event near 0.41 s.
    # Lower its pitch; eliminate long electronic tails instead of merely turning
    # down the original six-second multi-impact preview.
    energy = read(SOURCES/'LaserMagicImpacts.mp3', 0, .31, .80)
    energy = filt(energy, 60, 'highpass', 2)
    energy = bell(energy, 2400, -8, .8)
    energy = bell(energy, 3900, -10, 1.0)
    energy = filt(energy, 2850, 'lowpass', 4)
    mono = energy.mean(axis=1, keepdims=True)
    energy = mono + (energy-mono)*.35
    energy = peak(edge(energy, .004, .065))
    t = np.arange(len(energy))/SR
    energy *= np.exp(-t*3.6)[:, None]

    # A physical bow transient carries the identity of the weapon. Suppress its
    # sharp 2.7-4 kHz edge while keeping the initial string/shaft articulation.
    bow = read(ARROWS/'Bow.wav', .092, .36, .94)
    bow = filt(bow, 150, 'highpass', 2)
    bow = bell(bow, 3000, -5.5, .9)
    bow = filt(bow, 4800, 'lowpass', 3)
    bow = peak(edge(bow))
    wind = read(ARROWS/'swish_2.wav', .037, .235, .97)
    wind = peak(edge(filt(wind, [420, 2800], 'bandpass', 2), .008, .04))

    # Short warm reflections preserve a small magical residue without a ringing
    # laser note. They remain well below the dry bow and contact transient.
    residue = filt(energy, [450, 1900], 'bandpass', 2)
    residue = edge(residue, .015, .07)
    audio = np.zeros((round(.82*SR), 2), dtype=np.float64)
    mix_at(audio, wind, 0, .20)
    mix_at(audio, bow, .024, .72)
    mix_at(audio, energy, .056, .42)
    for delay, gain in [(.112, .10), (.178, .065), (.249, .035)]:
        mix_at(audio, residue, delay, gain)
    audio = edge(filt(audio, 45, 'highpass', 2), .003, .06)
    # Peak headroom only; no claim of perceptual equal-loudness matching.
    final_gain = 10**(-3.5/20)/max(1e-8, float(np.abs(audio).max()))
    audio *= final_gain
    single = OUT/'B2_GoldenBow_Impact.wav'
    audition = OUT/'B2_GoldenBow_Impact_2x.wav'
    sf.write(single, audio, SR, subtype='PCM_24')
    repeated = np.concatenate([audio, np.zeros((round(.65*SR), 2)), audio])
    sf.write(audition, repeated, SR, subtype='PCM_16')

    sources = [
        {'file': str(SOURCES/'LaserMagicImpacts.mp3'), 'title': 'Laser/Magic Spell Impacts',
         'author': 'TannerSound', 'page': 'https://freesound.org/people/TannerSound/sounds/842627/',
         'license': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
         'cut_seconds': [0, .31], 'speed_pitch_ratio': .80},
        {'file': str(ARROWS/'Bow.wav'), 'title': 'Battle Sound Effects / Bow.wav',
         'author': 'artisticdude', 'page': 'https://opengameart.org/content/battle-sound-effects',
         'license': 'CC0-1.0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
         'cut_seconds': [.092, .36], 'speed_pitch_ratio': .94},
        {'file': str(ARROWS/'swish_2.wav'), 'title': 'Battle Sound Effects / swish_2.wav',
         'author': 'artisticdude', 'page': 'https://opengameart.org/content/battle-sound-effects',
         'license': 'CC0-1.0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
         'cut_seconds': [.037, .235], 'speed_pitch_ratio': .97},
    ]
    for item in sources:
        item['sha256'] = hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()
    receipt = {'date': '2026-10-28', 'revision': 'B2 Golden Bow Impact',
        'user_direction': 'Reduce harshness and make candidate B read as a bow/arrow impact',
        'single_file': str(single), 'audition_file': str(audition), 'single_seconds': .82,
        'audition_repeats': 2, 'audition_gap_seconds': .65, 'sample_rate': SR, 'channels': 2,
        'peak_dbfs': -3.5, 'final_gain_db': float(20*np.log10(final_gain)),
        'processing': 'First B impact cropped, pitch/speed 0.8, mid/high de-emphasis, 2850 Hz low-pass; layer processed CC0 bow and swish; short low-level filtered reflections; no compression or hard clipping.',
        'sources': sources, 'user_listening_approved': False, 'imported_to_ue': False, 'runtime_modified': False}
    (OUT/'manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    credits = ['B2 Golden Bow Impact, 2026-10-28. Audition only; not integrated.',
               'Derivative of "Laser/Magic Spell Impacts" by TannerSound, CC BY 4.0.',
               'https://freesound.org/people/TannerSound/sounds/842627/',
               'https://creativecommons.org/licenses/by/4.0/',
               'Changes: crop first impact, lower pitch/speed, filter/EQ, mix physical bow/air layers, short filtered reflections, level adjustment.',
               'Additional layers: "Battle Sound Effects / Bow.wav and swish_2.wav" by artisticdude, CC0.',
               'https://opengameart.org/content/battle-sound-effects',
               'https://creativecommons.org/publicdomain/zero/1.0/']
    (OUT/'CREDITS.txt').write_text('\n'.join(credits), encoding='utf-8')
    print(json.dumps({'single': str(single), 'audition': str(audition), 'seconds': .82, 'runtime_modified': False}))


if __name__ == '__main__':
    main()
