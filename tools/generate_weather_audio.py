"""Original procedural weather audio: mono PCM, no external recordings/dependencies."""
import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'assets/sfx/weather'
RATE = 22050

def write(name, values):
    peak = max(abs(v) for v in values) or 1
    values = [int(v / peak * 24000) for v in values]
    with wave.open(str(ROOT / name), 'wb') as stream:
        stream.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        stream.writeframes(struct.pack('<' + 'h' * len(values), *values))
    print(name, 'seconds', len(values) / RATE, 'peak_pcm', max(map(abs, values)))

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(240907)
    values = []
    low = 0
    for i in range(RATE * 12):
        t = i / RATE
        white = rng.uniform(-1, 1)
        low = low * .97 + white * .03
        values.append((white * .13 + low * .85) * (.82 + .10 * math.sin(t * math.tau / 12)))
    # Crossfade the endpoints for a continuous rain loop.
    blend = RATE // 5
    for i in range(blend):
        a = i / blend
        values[i] = values[-blend+i] * (1-a) + values[i] * a
    write('rain_loop.wav', values[:-blend])
    for variant in range(1, 4):
        rng.seed(9910 + variant)
        values = []
        low = mid = 0
        for i in range(RATE * 7):
            t = i / RATE
            white = rng.uniform(-1, 1)
            low = low * .992 + white * .008
            mid = mid * .89 + white * .11
            rumble = low * 3.5 + mid * .22
            pulse = .65 + .25 * math.sin(t * 4.3 + variant) + .1 * math.sin(t * 9.2)
            attack = min(1, t / .018)
            tail = math.exp(-t / 1.9) * min(1, (7-t)/.5)
            crack = white * .13 * math.exp(-t / .075)
            values.append((rumble * pulse + crack) * attack * tail)
        write(f'thunder_{variant}.wav', values)

if __name__ == '__main__':
    main()
