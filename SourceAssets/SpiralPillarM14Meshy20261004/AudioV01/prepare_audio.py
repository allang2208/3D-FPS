"""Author the nine S_M14_* creature sounds for the SpiralPillar (stud pillar).

The pillar is wet organic tissue bolted with old metal hardware. Organic
layers reuse the CC0 freesound previews staged for M-10 in
../../M10ChenXia20261003/AudioScout; every hardware layer (stud clang, seam
creak, bolt rattle) is synthesized locally with numpy, so all outputs stay
license-clean. Output: 48000 Hz mono 16-bit PCM.
"""
import json, subprocess, wave
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
SCOUT = ROOT.parents[1] / "M10ChenXia20261003" / "AudioScout"
PREV = SCOUT / "Previews"
OGA = SCOUT / "OGA_Packs"
OUT = ROOT / "Audio"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "Records").mkdir(exist_ok=True)
SR = 48000
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(1410)


def load(path):
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
           "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def env_rms(y, win=0.05):
    n = max(1, int(win * SR))
    count = len(y) // n
    return np.sqrt((y[:count * n].reshape(count, n) ** 2).mean(axis=1))


def window(y, seconds, mode, offset=0.0):
    n = int(seconds * SR)
    if len(y) <= n:
        return y.copy()
    e = env_rms(y)
    w = max(1, int(seconds / 0.05))
    if mode == "attack":
        d = np.diff(e)
        i = int(np.argmax(d[int(offset / 0.05):-w]) + offset / 0.05)
    else:
        score = np.convolve(e, np.ones(w) / w, "valid")
        lo = int(offset / 0.05)
        if mode == "loud":
            i = int(np.argmax(score[lo:]) + lo)
        else:
            pct = 35.0 if mode == "calm" else 55.0
            target = np.percentile(score, pct)
            i = int(np.argmin(np.abs(score[lo:] - target)) + lo)
    return y[int(i * 0.05 * SR):int(i * 0.05 * SR) + n].copy()


def pitch(y, f):
    if abs(f - 1.0) < 1e-4:
        return y
    from math import gcd
    num, den = 1000, int(round(1000 * f))
    g = gcd(num, den)
    return resample_poly(y, num // g, den // g)


def band(y, lo, hi):
    return sosfilt(butter(3, [lo, hi], btype="bandpass", fs=SR, output="sos"), y)


def lowp(y, hi):
    return sosfilt(butter(3, hi, btype="lowpass", fs=SR, output="sos"), y)


def highp(y, lo):
    return sosfilt(butter(3, lo, btype="highpass", fs=SR, output="sos"), y)


def fade(y, fin=0.0, fout=0.0):
    t = np.arange(len(y)) / SR
    g = np.ones(len(y))
    if fin > 0:
        g *= np.clip(t / fin, 0, 1)
    if fout > 0:
        g *= np.clip((len(y) / SR - t) / fout, 0, 1)
    return y * g


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


def norm(y, peak):
    m = float(np.max(np.abs(y))) or 1.0
    return y * (peak / m)


def fit(y, seconds):
    n = int(round(seconds * SR))
    if len(y) < n:
        y = np.concatenate([y, np.zeros(n - len(y))])
    return y[:n]


def noise(dur):
    return rng.normal(0, 1, int(round(dur * SR)))


def chirp(dur, f0, f1, amp=1.0):
    t = np.arange(int(round(dur * SR))) / SR
    phase = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * dur))
    return np.sin(phase) * amp


def save(name, y):
    y = y - np.mean(y)
    peak = float(np.max(np.abs(y)))
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    f = OUT / (name + ".wav")
    with wave.open(str(f), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name}: {len(y)/SR:.2f}s peak={peak:.2f}")
    return {"file": str(f), "seconds": round(len(y) / SR, 3)}


# --- hardware helpers (fully synthesized, no external source) -----------------
def clang(dur, f0, stack=((1.0, .30, 12), (1.58, .18, 16), (2.53, .09, 20), (3.97, .04, 26))):
    """Old bolt strike: inharmonic stud partials + a high contact tick."""
    t = np.arange(int(round(dur * SR))) / SR
    y = np.zeros(len(t))
    for ratio, gain, decay in stack:
        f = f0 * ratio
        phase = 2 * np.pi * (f * t + f * .02 * .03 * (1 - np.exp(-t / .03)))
        y += gain * np.sin(phase) * np.exp(-t * decay)
    tick = band(noise(.008), 2800, 11000)
    y[:len(tick)] += tick * 1.2
    return y * (1 - np.exp(-t * 500))


def creak(dur, f0, f1, amp=1.0):
    """Slow strained-metal groan: low chirp plus rubbing noise."""
    t = np.arange(int(round(dur * SR))) / SR
    env = np.exp(-((t - dur * .55) / (dur * .42)) ** 2)
    rub = lowp(band(noise(dur), 90, 480), 480)
    return (lowp(chirp(dur, f0, f1, .5), 700) + rub * .5) * env * amp


def rattle(dur, rate0, rate1, f0=800, amp=1.0):
    """Sparse stud rattle: short clang bursts at a ramping density."""
    n = int(round(dur * SR))
    y = np.zeros(n)
    t = 0.03
    while t < dur - 0.03:
        rate = rate0 + (rate1 - rate0) * (t / dur)
        t += rng.exponential(1.0 / max(1.0, rate))
        w = int(rng.uniform(.03, .09) * SR)
        burst = clang(w / SR, f0 * rng.uniform(.85, 1.2),
                      ((1, .3, 18), (1.58, .16, 22), (2.53, .07, 28)))
        i = int(t * SR)
        if i + w < n:
            y[i:i + w] += burst[:w] * rng.uniform(.4, 1.0)
    return y * amp


SRC = {
    "growl": load(PREV / "621005_samsterbirdies_deep_scary_growl_9s_CC0.mp3"),
    "squelch": load(PREV / "635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3"),
    "valve_hiss": load(ROOT / "Scout" / "457294_brunoboselli_pressure_release_CC0.mp3"),  # retained source; unused since the spit windup was cut
    "acid_spit": load(ROOT / "Scout" / "568598_thesoundbandit_spit_acid_CC0.mp3"),
    "air_burst": load(ROOT / "Scout" / "138477_justinvoke_air_burst_CC0.mp3"),
    "wetmove": load(PREV / "834075_federicoy_wet_slimy_movement_96s_CC0.mp3"),
    "bite": load(PREV / "467701_lucasduff_monster_bite_2s_CC0.mp3"),
    "snarl_attack": load(PREV / "466830_breviceps_dragon_snarl_roar_attack_3s_CC0.mp3"),
}
manifest = {}

# Idle was withdrawn on user feedback (too busy, no character); the pillar stays
# silent at rest. S_M14_Idle is deleted from Content by the importer.

# --- S_M14_Crawl: 2.6 s eight-toe drag loop + seam rattle ----------------------
dur = 2.6
wet = pitch(window(SRC["wetmove"], 3.0, "steady", offset=8.0), 0.7)
wet = fit(band(wet, 60, 2100), 3.0)
wet = fit(loopify(wet, 0.4), dur)
y = wet.copy()
for i, at in enumerate((0.05, 0.4, 0.72, 1.05, 1.38, 1.7, 2.02, 2.35)):
    scrape = lowp(band(noise(.24), 150 + 60 * (i % 3), 900 + 120 * (i % 3)), 1200)
    place(y, scrape * np.exp(-np.arange(len(scrape)) / SR * (7 + i % 2 * 3)),
          at + rng.uniform(-.015, .015), .34 + .05 * (i % 2))
rattle_bed = fit(loopify(rattle(dur + .4, 1.5, 2.5, f0=900, amp=.5), .4), dur)
y = norm(y * .9 + rattle_bed * .5, .5)
manifest["S_M14_Crawl"] = save("S_M14_Crawl", y)

# --- S_M14_Bite: 1.15 s lunge + jaw snap at the 0.86 s contact -----------------
dur = 1.15
y = np.zeros(int(dur * SR))
lunge = pitch(SRC["snarl_attack"], 1.0)[: int(0.8 * SR)]
lunge = lowp(fade(lunge, 0.15, 0.1), 1500)
place(y, lunge, 0.02, .32)
snap = pitch(SRC["bite"], 1.05)
e = env_rms(snap)
onset = int(np.argmax(np.diff(e)) * 0.05 * SR)
snap = band(snap[onset:onset + int(0.7 * SR)], 130, 7000)
peak_at = int(np.argmax(np.abs(snap[: int(0.4 * SR)])))
place(y, snap, 0.86 - peak_at / SR, 1.0)
wet = window(SRC["squelch"], 0.4, "attack", offset=20.0)
place(y, lowp(wet, 2400), 0.89, .45)
place(y, clang(.25, 300), 0.86, .3)
manifest["S_M14_Bite"] = save("S_M14_Bite", norm(fade(y, .01, .3), .85))

# --- S_M14_Spit: 1.3 s pressure windup -> acid jet at 1.10 s -------------------
# V03 (user feedback: squelch family too cartoonish, source retired). All watery
# gurgle is gone. Release = a recorded acid-spit attack over an air-burst crack,
# with a sub shove and short spray tail.
# V04 (user: no windup cue): the first 1.05 s stays silent so only the jet is
# heard at the 1.10 s release point.
dur = 1.3
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
place(y, band(SRC["air_burst"], 800, 9000), 1.10, .85)
acid = window(SRC["acid_spit"], .55, "attack")
acid = band(acid, 150, 5500)
peak_at = int(np.argmax(np.abs(acid[: int(.2 * SR)])))
place(y, acid, 1.10 - peak_at / SR, .8)
tt = np.arange(int(.22 * SR)) / SR
place(y, np.sin(2 * np.pi * (95 - 35 * tt) * tt) * np.exp(-tt * 11), 1.10, .5)
tail = band(noise(.22), 2600, 9000) * np.exp(-np.arange(int(.22 * SR)) / SR * 11)
place(y, tail, 1.14, .2)
y[: int(1.08 * SR)] = 0.0
manifest["S_M14_Spit"] = save("S_M14_Spit", norm(fade(y, .01, .22), .8))

# --- S_M14_SpitImpact: 0.8 s venom splat at the hit point -----------------------
dur = 0.8
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
splat = pitch(window(SRC["squelch"], .5, "attack", offset=2.0), 1.0)
place(y, band(splat, 200, 6000), 0.01, 1.0)
tt = np.arange(int(.2 * SR)) / SR
thump = np.sin(2 * np.pi * (70 - 18 * tt) * tt) * np.exp(-tt * 14)
place(y, thump, .01, .7)
hiss = band(noise(.55), 2600, 9000) * np.exp(-t[: int(.55 * SR)] * 6)
place(y, hiss, .08, .22)
for at in (.30, .48, .66):
    drip = chirp(.05, rng.uniform(700, 1100), rng.uniform(300, 450), .2)
    place(y, drip, at + rng.uniform(-.02, .02), .35)
manifest["S_M14_SpitImpact"] = save("S_M14_SpitImpact", norm(fade(y, .004, .3), .8))

# --- S_M14_TrunkSlam: 1.5 s windup -> body slam at 1.20 s -----------------------
dur = 1.5
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
place(y, creak(1.05, 160, 260, .6) * np.clip(t[: int(1.05 * SR)] / 1.05, .2, 1), .05, .55)
groan = pitch(SRC["growl"], 0.8)[: int(1.0 * SR)]
groan = lowp(groan, 900) * np.clip(np.arange(len(groan)) / (1.0 * SR), 0, 1)
place(y, groan, .1, .28)
tt = np.arange(int(.5 * SR)) / SR
thump = np.sin(2 * np.pi * (52 - 11 * tt) * tt) * np.exp(-tt * 7)
slam_body = pitch(window(SRC["wetmove"], .4, "attack", offset=55.0), 0.7)
y_slam = band(slam_body, 60, 2600)
place(y, y_slam, 1.20, .9)
place(y, thump, 1.21, .9)
place(y, clang(.5, 190, ((1, .32, 7), (1.58, .18, 9), (2.53, .08, 11))), 1.20, .55)
rumble = lowp(np.cumsum(noise(.6)), 200)
place(y, rumble / np.max(np.abs(rumble)) * np.exp(-np.arange(len(rumble)) / SR * 4), 1.24, .4)
manifest["S_M14_TrunkSlam"] = save("S_M14_TrunkSlam", norm(fade(y, .01, .4), .88))

# --- S_M14_Whirlwind: 3.3 s — ready 0.55, six turns 0.55-2.65, recover ---------
dur = 3.3
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
spin_env = np.clip((t - .55) / .18, 0, 1) * np.clip((2.68 - t) / .30, 0, 1)
spin_env *= np.clip(t / .4, 0, 1)
whoosh = band(noise(dur), 200, 2600)
lobes = .55 + .45 * np.abs(np.sin(np.pi * 2.86 * np.clip(t - .55, 0, None)))
y += whoosh * spin_env * lobes * .8
strain = lowp(chirp(2.1, 90, 55, .5), 500)
place(y, strain * spin_env[: int(2.1 * SR)], .55, .5)
place(y, creak(.5, 170, 120, .6), .15, .4)
rattle_spin = rattle(2.2, 2, 6, f0=750, amp=.5)
rattle_spin = rattle_spin * spin_env[: len(rattle_spin)]
place(y, rattle_spin, .5, .5)
recover = band(noise(.7), 120, 1200) * np.exp(-np.arange(int(.7 * SR)) / SR * 4)
place(y, recover, 2.62, .5)
manifest["S_M14_Whirlwind"] = save("S_M14_Whirlwind", norm(fade(y, .02, .45), .8))

# --- S_M14_Hit: 0.7 s wet impact + hardware ring --------------------------------
dur = 0.7
y = np.zeros(int(dur * SR))
sq = pitch(window(SRC["squelch"], 0.45, "attack", offset=40.0), 0.9)
sq = band(sq, 140, 4000)[: int(0.4 * SR)]
place(y, sq, 0.01, 1.0)
tt = np.arange(int(.25 * SR)) / SR
thump = np.sin(2 * np.pi * (58 - 13 * tt) * tt) * np.exp(-tt * 11)
place(y, thump, 0.012, .75)
place(y, clang(.3, 340, ((1, .25, 14), (1.58, .12, 18))), 0.02, .35)
manifest["S_M14_Hit"] = save("S_M14_Hit", norm(y, .8))

# --- S_M14_Death: 2.6 s groan -> tissue slump -> hardware clatter ---------------
dur = 2.6
t = np.arange(int(dur * SR)) / SR
y = np.zeros(int(dur * SR))
moan = pitch(SRC["growl"], 0.6)[: int(1.3 * SR)]
moan = lowp(moan, 550) * np.clip(1.15 - np.arange(len(moan)) / (1.3 * SR), 0, 1)
place(y, moan, 0.0, .8)
slump = pitch(window(SRC["wetmove"], 1.0, "steady", offset=60.0), 0.6)
place(y, band(slump, 60, 2200), .55, .85)
splat = pitch(window(SRC["squelch"], .5, "attack", offset=45.0), 0.75)
place(y, band(splat, 80, 2600), 1.40, .9)
for i, at in enumerate((1.45, 1.62, 1.85)):
    place(y, clang(.4, 220 * (1 + .15 * i),
                   ((1, .3, 8), (1.58, .16, 10), (2.53, .07, 13))), at, .6 - .12 * i)
tt = np.arange(int(.45 * SR)) / SR
thump = np.sin(2 * np.pi * (46 - 10 * tt) * tt) * np.exp(-tt * 8)
place(y, thump, 1.44, .8)
manifest["S_M14_Death"] = save("S_M14_Death", norm(fade(y, .02, .7), .85))

provenance = {
    "pipeline": "CC0 previews staged in M10 AudioScout -> deterministic slice/pitch/layer + fully synthesized hardware layers in prepare_audio.py -> 48000 Hz mono PCM",
    "note": "Organic layers reuse the same freesound CC0 previews as M-10/M-25 V1; swap for original WAVs when a freesound account download is available. Hardware layers (stud clang, seam creak, bolt rattle) are pure synthesis and carry no external rights.",
    "sources": {
        "621005": {"author": "SamsterBirdies", "license": "CC0", "url": "https://freesound.org/s/621005/", "used_in": ["S_M14_TrunkSlam", "S_M14_Death"]},
        "635042": {"author": "sillygrizzlies", "license": "CC0", "url": "https://freesound.org/s/635042/", "used_in": ["S_M14_Bite", "S_M14_SpitImpact", "S_M14_Hit", "S_M14_Death"]},
        "457294": {"author": "brunoboselli", "license": "CC0", "url": "https://freesound.org/s/457294/", "used_in": []},
        "568598": {"author": "TheSoundBandit", "license": "CC0", "url": "https://freesound.org/s/568598/", "used_in": ["S_M14_Spit"]},
        "138477": {"author": "JustInvoke", "license": "CC0", "url": "https://freesound.org/s/138477/", "used_in": ["S_M14_Spit"]},
        "834075": {"author": "Federicoy", "license": "CC0", "url": "https://freesound.org/s/834075/", "used_in": ["S_M14_Crawl", "S_M14_TrunkSlam", "S_M14_Death"]},
        "467701": {"author": "LucasDuff", "license": "CC0", "url": "https://freesound.org/s/467701/", "used_in": ["S_M14_Bite"]},
        "466830": {"author": "Breviceps", "license": "CC0", "url": "https://freesound.org/s/466830/", "used_in": ["S_M14_Bite"]},
    },
    "outputs": manifest,
    "tested": False,
}
(ROOT / "Records" / "audio_source.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("M14_AUDIO_V01_PREPARED")
