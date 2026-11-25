"""Cut individual ground contacts from the two CC0 horse recordings."""
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SOURCE = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageStable/HoofAudioR11"
OUTPUT_RATE = 48000

# Each interval contains one impact and its own short decay, ending before the next strike.
CUTS = {
    "Walk": ("WalkPath1854.ogg", [
        (22.690, 22.803), (23.187, 23.331), (29.334, 29.475), (31.359, 31.509)]),
    "Canter": ("Galopp564628.ogg", [
        (3.837, 3.951), (4.171, 4.247), (5.796, 5.888), (6.280, 6.404)]),
}


def prepare():
    dest = SOURCE / "Masters"
    dest.mkdir(parents=True, exist_ok=True)
    for gait, (source, intervals) in CUTS.items():
        recording, rate = sf.read(SOURCE / "Originals" / source, always_2d=True)
        mono = recording.mean(axis=1)
        # Remove wind rumble once on the continuous recording to avoid filter startup at each cut.
        highpass = signal.butter(2, 48, fs=rate, btype="highpass", output="sos")
        mono = signal.sosfilt(highpass, mono)
        for index, (start, stop) in enumerate(intervals, 1):
            take = mono[round(start*rate):round(stop*rate)]
            divisor = gcd(rate, OUTPUT_RATE)
            take = signal.resample_poly(take, OUTPUT_RATE//divisor, rate//divisor)
            attack, release = 48, 576
            take[:attack] *= np.linspace(0, 1, attack)
            take[-release:] *= np.cos(np.linspace(0, np.pi/2, release))**2
            take *= 0.80 / np.max(np.abs(take))
            sf.write(dest / f"SW_Hoof_{gait}_{index:02}.wav", take, OUTPUT_RATE, subtype="PCM_24")


if __name__ == "__main__":
    prepare()
