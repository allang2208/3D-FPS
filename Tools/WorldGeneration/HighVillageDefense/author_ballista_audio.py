"""Build mono ballista cues from the project's CC0 Still North recordings."""
import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfilt

RATE = 48000
SOURCE = Path(__file__).resolve().parents[3] / 'SourceAssets/BowAudioStillNorth20260926/Wav'


def sample(name):
    rate, data = wavfile.read(SOURCE / ('S_Bow_' + name + '.wav'))
    if rate != RATE or data.ndim != 1 or data.dtype != np.int16:
        raise ValueError(f'Expected 48 kHz mono PCM16: {name}')
    return data.astype(np.float64) / 32768.


def seconds(duration):
    return np.arange(round(duration * RATE)) / RATE


def trim_edges(x, attack, release):
    x = x.copy()
    a, r = round(attack * RATE), round(release * RATE)
    x[:a] *= np.linspace(0., 1., a)
    x[-r:] *= np.linspace(1., 0., r)
    return x


def layer(out, source, at, gain):
    start = round(at * RATE)
    part = out[start:start + len(source)]
    part += gain * source[:len(part)]


def lowpass(source, hz):
    return sosfilt(butter(2, hz, fs=RATE, output='sos'), source)


def wood_knock(duration):
    t = seconds(duration)
    return (1.-np.exp(-t/.002)) * (
        .64*np.sin(2*np.pi*103*t)*np.exp(-t/.074) +
        .32*np.sin(2*np.pi*188*t+.4)*np.exp(-t/.045) +
        .16*np.sin(2*np.pi*327*t+.2)*np.exp(-t/.028))


def save(folder, name, mix, headroom_db):
    mix = trim_edges(mix, .001, .016)
    mix *= 10**(headroom_db/20) / np.max(np.abs(mix))
    wavfile.write(folder / ('S_Ballista' + name + '.wav'), RATE,
                  np.rint(mix*32767).astype('<i2'))


def author(folder):
    folder.mkdir(parents=True, exist_ok=True)
    draw, nock, release = (sample(k) for k in ('Draw', 'Nock', 'Release'))
    latch_start = max(0, int(np.argmax(np.abs(nock))) - round(.006*RATE))
    latch = trim_edges(nock[latch_start:latch_start+round(.065*RATE)], .001, .009)
    knock = wood_knock(.26)

    # A loaded carriage settles into tension just before the catch opens.
    tension = np.zeros_like(seconds(.51))
    bite = draw[round(.32*RATE):round(.71*RATE)]
    layer(tension, trim_edges(resample_poly(bite, 5, 4), .04, .045), 0, .75)
    layer(tension, lowpass(latch, 2400), .39, .26)
    save(folder, 'Tension', tension, -9.)

    # Preserve the recorded string transient; the slower low band gives the frame weight.
    loose = np.zeros_like(seconds(.75))
    layer(loose, release, 0, .83)
    layer(loose, lowpass(resample_poly(release, 3, 2), 1600), .009, .54)
    layer(loose, knock, .018, .65)
    layer(loose, lowpass(knock, 560), .089, .16)
    save(folder, 'Release', loose, -3.)

    # Two crank strokes across the actual return animation, ending on a seated pawl.
    winch = np.zeros_like(seconds(2.05))
    layer(winch, lowpass(resample_poly(draw, 7, 5), 3800), .025, .61)
    rng = np.random.default_rng(1124)
    for start in (.055, 1.015):
        for i, offset in enumerate((0., .145, .268, .379, .489, .610, .748)):
            tick = lowpass(resample_poly(latch, int(rng.integers(96, 117)), 92), 3300)
            layer(winch, tick, start + offset, (.56 if i in (0, 6) else .36) * rng.uniform(.8, 1.1))
    layer(winch, latch, 1.935, .64)
    layer(winch, knock, 1.939, .17)
    save(folder, 'Windlass', winch, -7.)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    author(parser.parse_args().output)
