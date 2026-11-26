"""Create the trebuchet action and impact cues from project foley and CC0 recordings."""
import argparse
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

from author_ballista_audio import RATE, layer, lowpass, seconds, trim_edges

SOURCES = Path(__file__).resolve().parents[3] / 'SourceAssets'
DOOR = 'DoorAudio20261003/Source/DoorSet/qubodup-DoorSet/flac/qubodup-DoorOpen08.flac'
ROPE = 'BowAudioStillNorth20260926/Wav/S_Bow_Draw.wav'
SURFACES = 'SurfaceImpacts20260914'


def recording(relative_path):
    audio, rate = sf.read(SOURCES / relative_path, always_2d=True)
    mono = audio.mean(axis=1)
    divisor = gcd(rate, RATE)
    mono = resample_poly(mono, RATE // divisor, rate // divisor)
    start = np.flatnonzero(np.abs(mono) > .015 * np.max(np.abs(mono)))[0]
    mono = mono[max(0, start - round(.006 * RATE)):]
    return mono / np.max(np.abs(mono))


def frame_resonance(duration, pitch):
    t = seconds(duration)
    bands = sum(gain * np.sin(2*np.pi*pitch*ratio*t) * np.exp(-t/decay)
                for ratio, gain, decay in ((1., .61, .14), (1.63, .33, .085), (3.23, .16, .045)))
    return bands * (1.-np.exp(-t/.003))


def sweep(rng, duration, low, high):
    t = seconds(duration)
    band = butter(2, [low, high], btype='bandpass', fs=RATE, output='sos')
    air = sosfilt(band, rng.standard_normal(len(t)))
    return air / np.max(np.abs(air)) * np.sin(np.pi*t/duration)**1.35


def save(folder, role, mix, peak_db):
    mix = trim_edges(mix, .001, .025)
    mix *= 10**(peak_db/20) / np.max(np.abs(mix))
    sf.write(folder / ('S_Trebuchet' + role + '.wav'), mix, RATE, subtype='PCM_16')


def author(folder):
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(112406)
    hinge = lowpass(resample_poly(recording(DOOR), 3, 2), 1850)
    draw = recording(ROPE)
    wood = recording(f'{SURFACES}/Impact_Wood_1.wav')
    stone = recording(f'{SURFACES}/Impact_Stone_1.wav')
    grit = recording(f'{SURFACES}/Impact_Dirt_0.wav')

    # Take up slack, then accelerate the heavy pivot at 0.64 s.
    windup = np.zeros_like(seconds(1.08))
    layer(windup, trim_edges(draw[:round(.64*RATE)], .045, .07), .035, .29)
    layer(windup, lowpass(wood, 1500), .59, .17)
    layer(windup, trim_edges(hinge[:round(.44*RATE)], .008, .035), .635, .43)
    layer(windup, sweep(rng, .31, 130, 1450), .77, .33)
    save(folder, 'Windup', windup, -10.)

    # From sling release: passing air, the beam braking at 1.31 s, then lighter rebound.
    throw = np.zeros_like(seconds(1.4))
    layer(throw, sweep(rng, .27, 350, 3900), 0., .83)
    layer(throw, lowpass(wood, 3000), .018, .29)
    layer(throw, frame_resonance(.84, 72.), .222, .86)
    layer(throw, lowpass(resample_poly(wood, 5, 3), 1900), .23, .65)
    layer(throw, lowpass(hinge, 1200), .27, .27)
    layer(throw, frame_resonance(.48, 94.), .73, .15)
    save(folder, 'Release', throw, -3.5)

    # Four uneven hauling strokes. The pouch receives its next stone near the end.
    reload = np.zeros_like(seconds(4.78))
    for at, ratio, gain in ((.04, 1.32, .5), (1.16, 1.49, .57),
                             (2.34, 1.26, .53), (3.39, 1.42, .43)):
        rub = resample_poly(draw, round(ratio*100), 100)[:round(.85*RATE)]
        layer(reload, trim_edges(lowpass(rub, 2200), .065, .11), at, gain)
        layer(reload, trim_edges(hinge[:round(.57*RATE)], .035, .09), at+.24, gain*.49)
        layer(reload, lowpass(wood, 1700), at+.88, gain*.32)
    layer(reload, lowpass(stone, 1450), 4.58, .52)
    layer(reload, frame_resonance(.17, 101.), 4.59, .29)
    save(folder, 'Reload', reload, -9.)

    # A short contact transient and low ground impulse, followed by scattered grit.
    impact = np.zeros_like(seconds(1.16))
    layer(impact, lowpass(stone, 4200), 0., .82)
    layer(impact, lowpass(resample_poly(grit, 5, 2), 900), .008, .95)
    layer(impact, frame_resonance(.91, 53.), .012, .82)
    for at, ratio, gain in ((.09, 1.41, .36), (.17, .97, .2),
                             (.31, 1.22, .16), (.46, .86, .105), (.69, 1.13, .065)):
        layer(impact, resample_poly(stone, round(ratio*100), 100), at, gain)
    save(folder, 'Impact', impact, -3.)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    author(parser.parse_args().output)
