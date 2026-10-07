"""M09 AudioV01: original local synthesis, same membrane-chime voice as Resonance V07.

Fills the gaps the V04 cue set left: idle bell shimmer + travel hand-over-hand
crawl loops, a real death arc (detune -> tear -> fall -> floor clang) and
membrane-textured swing/claw/stagger upgrades. No sampled third-party audio.
Outputs 48000 Hz mono 16-bit PCM to AudioV01/Audio.
"""
import json, wave
import numpy as np
from pathlib import Path
from scipy.signal import butter, sosfilt

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/AudioV01')
(OUT / 'Audio').mkdir(parents=True, exist_ok=True)
(OUT / 'Records').mkdir(exist_ok=True)
SR = 48000
rng = np.random.default_rng(91)


def band(y, lo, hi):
    return sosfilt(butter(3, [lo, hi], btype='bandpass', fs=SR, output='sos'), y)


def lowp(y, hi):
    return sosfilt(butter(3, hi, btype='lowpass', fs=SR, output='sos'), y)


def fade(y, fin, fout, sr=SR):
    t = np.arange(len(y)) / sr
    return y * np.clip(t / fin, 0, 1) * np.clip((len(y) / sr - t) / fout, 0, 1)


def loopify(y, xf):
    n = int(round(xf * SR))
    m = len(y) - n
    if m <= n:
        return y
    r = np.arange(n) / max(1, n - 1)
    out = np.empty(m)
    out[:m - n] = y[n:m]
    out[m - n:] = y[m:m + n] * (1 - r) + y[:n] * r
    return out


def place(base, layer, at, gain=1.0):
    i = int(at * SR)
    j = min(len(base), i + len(layer))
    if j > i:
        base[i:j] += layer[:j - i] * gain
    return base


def chirp(dur, f0, f1, amp=1.0):
    t = np.arange(int(round(dur * SR))) / SR
    phase = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur))
    return np.sin(phase) * amp


def modal(t0, f0, stack, dur_total, relax=.045):
    """Tensioned-membrane bell strike at t0: (ratio, gain, decay) partials with
    the V07 downward pitch relaxation."""
    t = np.arange(int(round(dur_total * SR))) / SR
    age = np.maximum(t - t0, 0)
    attack = (t >= t0) * (1 - np.exp(-age * 260))
    body = np.zeros_like(t)
    for ratio, gain, decay in stack:
        f = f0 * ratio
        phase = 2 * np.pi * (f * age + f * .055 * relax * (1 - np.exp(-age / relax)))
        body += gain * np.sin(phase) * np.exp(-age * decay)
    return attack * body


def noise(dur):
    return rng.normal(0, 1, int(round(dur * SR)))


def norm(y, peak):
    y = y - np.mean(y)
    return y * (peak / max(peak, float(np.max(np.abs(y)))))


def save(name, y, seconds):
    data = (np.clip(y, -1, 1) * 32767).astype('<i2')
    f = OUT / 'Audio' / (name + '.wav')
    with wave.open(str(f), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f'{name}: {len(y)/SR:.2f}s')
    return {'file': str(f), 'seconds': seconds}


manifest = {}
BELL = ((1.0, .26, 4.5), (1.47, .17, 6.2), (2.19, .08, 7.8), (3.38, .04, 11.0))

# --- S_M09_Idle: 3.6 s bell-body shimmer + membrane breath loop ----------------
dur, xf = 3.6, .8
t = np.arange(int(round((dur + xf) * SR))) / SR
shimmer = np.zeros(len(t))
for i, (f, g) in enumerate(((55, .05), (80.9, .035), (120.5, .02), (185.9, .011))):
    beat = .72 + .28 * np.sin(2 * np.pi * (.21 + .09 * i) * t + i * 1.7)
    shimmer += g * np.sin(2 * np.pi * f * t) * beat
breath = band(noise(dur + xf), 170, 680) * (.5 + .5 * np.sin(2 * np.pi * .28 * t)) * .5
y = loopify(shimmer + lowp(breath, 900), xf)
creak = lowp(chirp(.38, 240, 165, .5), 900) * np.exp(-np.arange(int(.38 * SR)) / SR * 5)
place(y, creak, .9, .16); place(y, creak * .8, 2.5, .12)
manifest['S_M09_Idle'] = save('S_M09_Idle', norm(fade(y, .01, .01), .30), dur)

# --- S_M09_Travel: 2.4 s hand-over-hand ceiling crawl loop ---------------------
dur, xf = 2.4, .5
t = np.arange(int(round((dur + xf) * SR))) / SR
sway = .018 * np.sin(2 * np.pi * (55 * t + .9 * np.sin(2 * np.pi * .42 * t)))
base = loopify(lowp(band(noise(dur + xf), 140, 900), 800) * .05 + sway, xf)
for i, at in enumerate((.12, .72, 1.32, 1.92)):
    thud = np.sin(2 * np.pi * (62 - 9 * np.arange(int(.09 * SR)) / SR) * np.arange(int(.09 * SR)) / SR) \
        * np.exp(-np.arange(int(.09 * SR)) / SR * 26)
    place(base, thud, at, .5)
    sc = band(noise(.34), 420 + 180 * (i % 2), 1350 + 220 * (i % 2))
    place(base, sc * np.exp(-np.arange(len(sc)) / SR * (6 + i % 2 * 3)), at + .02, .30)
manifest['S_M09_Travel'] = save('S_M09_Travel', norm(fade(base, .01, .01), .42), dur)

# --- S_M09_Swing L/R: 2.3 s membrane-slice whoosh, contact ~1.02 s -------------
def swing(seed_shift, peak_at, center):
    dur = 2.3
    t = np.arange(int(round(dur * SR))) / SR
    env = np.exp(-((t - peak_at) / .16) ** 2)
    slice_hi = band(noise(dur), center, 5200) * env
    slice_lo = band(noise(dur), 260, 1200) * np.exp(-((t - peak_at + .03) / .2) ** 2)
    ring = modal(peak_at - .02, 615 + seed_shift * 35,
                 ((1, .22, 16), (1.51, .13, 20), (2.25, .06, 26)), dur)
    dip = chirp(.5, 68, 34, .4) * np.exp(-np.arange(int(.5 * SR)) / SR * 4)
    y = slice_hi * .75 + slice_lo * .8 + ring
    place(y, lowp(dip, 300), peak_at - .05, .5)
    return fade(y, .01, .3), dur

y, dur = swing(0, 1.02, 1500)
manifest['S_M09_SwingLeft'] = save('S_M09_SwingLeft', norm(y, .68), dur)
y, dur = swing(1, 1.00, 1350)
manifest['S_M09_SwingRight'] = save('S_M09_SwingRight', norm(y, .68), dur)

# --- S_M09_Claw: 1.1 s membrane slice + metallic snap at 0.44 s ----------------
dur = 1.1
t = np.arange(int(round(dur * SR))) / SR
lead = band(noise(dur), 500, 3400) * np.exp(-((t - .40) / .07) ** 2)
click = band(noise(.006), 2200, 9000)
ring = modal(.44, 615, ((1, .3, 14), (1.51, .18, 18), (2.24, .09, 24)), dur)
body = band(noise(dur), 90, 700) * np.exp(-((t - .5) / .12) ** 2)
y = lead * .8 + body * .35 + ring
place(y, click, .44, .9)
manifest['S_M09_Claw'] = save('S_M09_Claw', norm(fade(y, .005, .25), .78), dur)

# --- S_M09_Stagger: 1.4 s dull bell hit + membrane flinch -----------------------
dur = 1.4
t = np.arange(int(round(dur * SR))) / SR
hit = modal(.05, 92, ((1, .3, 7), (1.47, .2, 9), (2.19, .09, 12)), dur)
flinch = band(noise(dur), 300, 2200) * np.exp(-((t - .12) / .10) ** 2)
sag = chirp(.7, 130, 70, .3) * np.exp(-np.arange(int(.7 * SR)) / SR * 5)
y = hit + flinch * .6
place(y, lowp(sag, 600), .1, .6)
manifest['S_M09_Stagger'] = save('S_M09_Stagger', norm(fade(y, .004, .4), .70), dur)

# --- S_M09_Death: 2.4 s detune -> tear -> fall whoosh -> floor clang ------------
dur = 2.4
t = np.arange(int(round(dur * SR))) / SR
y = np.zeros(len(t))
# Bell slides ~9% flat while it lets go; then a membrane tear at 0.52 s.
for ratio, gain, dec in ((1, .3, 5), (1.47, .18, 6.5), (2.19, .08, 8)):
    f = 55 * ratio
    drift = 2 * np.pi * f * (t[:int(.55 * SR)] + -.045 * t[:int(.55 * SR)] ** 2 / .55)
    seg = np.sin(drift) * np.exp(-t[:int(.55 * SR)] * dec * .6)
    place(y, seg * np.clip(1.15 - t[:int(.55 * SR)] * 1.6, 0, 1), 0, gain)
tear = band(noise(.2), 750, 3200) * np.exp(-np.arange(int(.2 * SR)) / SR * 16)
place(y, tear, .52, .65)
whoosh = band(noise(.78), 300, 2400)
env = np.exp(-((np.arange(len(whoosh)) / SR - .34) / .3) ** 2)
swoop = chirp(.78, 470, 105, .5)
fall = whoosh * env * .7 + lowp(swoop, 2200) * env
place(y, fall, .62, .8)
clang = modal(1.48, 68, BELL, .9)
thud = np.sin(2 * np.pi * (46 - 9 * np.arange(int(.4 * SR)) / SR) * np.arange(int(.4 * SR)) / SR) \
    * np.exp(-np.arange(int(.4 * SR)) / SR * 9)
splat = lowp(band(noise(.3), 120, 1400), 1400) * np.exp(-np.arange(int(.3 * SR)) / SR * 10)
place(y, clang, 0, 1.0); place(y, thud, 1.49, .8); place(y, splat, 1.5, .5)
manifest['S_M09_Death'] = save('S_M09_Death', norm(fade(y, .005, .5), .85), dur)

# --- S_M09_Alert: 1.2 s spot stinger; the bell notices prey --------------------
# A quiet dark bell wake: two beating partials a semitone apart, membrane flinch,
# low pressure swell. Telegraph, not an attack hit.
dur = 1.2
t = np.arange(int(round(dur * SR))) / SR
wake = modal(.04, 98, ((1, .30, 3.4), (1.059, .22, 3.0), (1.47, .12, 5.0), (2.19, .05, 7.0)), dur)
flinch = band(noise(dur), 260, 1600) * np.exp(-((t - .16) / .09) ** 2)
swell = chirp(.6, 42, 58, .5) * np.exp(-np.arange(int(.6 * SR)) / SR * 3.5)
y = wake + flinch * .3
place(y, lowp(swell, 300), .1, .5)
manifest['S_M09_Alert'] = save('S_M09_Alert', norm(fade(y, .004, .35), .55), dur)

# --- S_M09_RingDown: 4.0 s emptied-bell decay after Resonance -------------------
# Voice->Stop() hard-cuts the resonance bed at state exit; this tail covers it:
# the last pulse fundamental ringing down with slow beating, a falling shimmer,
# and a membrane-relax creak.
dur = 4.0
t = np.arange(int(round(dur * SR))) / SR
ring = np.zeros(len(t))
for i, (ratio, gain, dec) in enumerate(((1, .30, 1.15), (1.007, .20, 1.3), (1.58, .13, 1.7),
                                      (2.55, .07, 2.2), (3.92, .035, 2.8))):
    ring += gain * np.sin(2 * np.pi * 98 * ratio * t + i * .7) * np.exp(-t * dec)
shim = band(noise(dur), 2600, 7200) * np.exp(-t * 2.4) * .12
relax = chirp(.5, 210, 130, .4) * np.exp(-np.arange(int(.5 * SR)) / SR * 4)
y = ring + shim
place(y, lowp(relax, 800), .55, .3)
manifest['S_M09_RingDown'] = save('S_M09_RingDown', norm(fade(y, .002, .6), .42), dur)

(OUT / 'Records' / 'audio_source.json').write_text(json.dumps({
    'pipeline': 'Original local procedural synthesis; no sampled third-party audio',
    'voice': 'M09 membrane-chime family shared with Resonance V07 (modal 1/1.47/2.19/3.38 stack + pitch relaxation)',
    'sample_rate': SR,
    'outputs': manifest,
    'tested': False}, indent=2), encoding='utf8')
print('M09_AUDIO_V01_PREPARED')
