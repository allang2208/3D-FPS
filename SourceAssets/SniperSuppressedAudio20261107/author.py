"""Master the existing suppressed one-shots at their original speed and stereo width."""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import lfilter, resample_poly


HERE = Path(__file__).resolve().parent
RATE = 48000
BANK = "/Game/Weapons/RifleSuppressedAudio20261015"
M24 = "/Game/Weapons/M24/FireAudio20261104"

# Low-mid body, attack presence, high shelf, and late-tail level (dB).
PROFILES = {
    "M24": ((205, .85), (1520, -1.9), (2850, -4.1), -.55),
    "SVD": ((198, 1.35), (1420, -1.65), (3100, -3.7), -.8),
    "SVCh": ((225, 1.05), (1690, -2.4), (2470, -4.7), -1.8),
}


def equalize(x, hz, gain_db, shelf=False):
    a = 10**(gain_db/40)
    w = 2*np.pi*hz/RATE
    c = np.cos(w)
    if shelf:
        beta = np.sqrt(2*a)*np.sin(w)
        b = a*np.array([(a+1)+(a-1)*c+beta, -2*((a-1)+(a+1)*c), (a+1)+(a-1)*c-beta])
        den = [(a+1)-(a-1)*c+beta, 2*((a-1)-(a+1)*c), (a+1)-(a-1)*c-beta]
    else:
        alpha = np.sin(w)/(2*.85)
        b = [1+alpha*a, -2*c, 1-alpha*a]
        den = [1+alpha/a, -2*c, 1-alpha/a]
    return lfilter(b, den, x, axis=0)


def exposure(x):
    # Ungated BS.1770-weighted shot energy. Use both channels with a common gain.
    y = lfilter([1.53512486,-2.69169619,1.19839281], [1,-1.69065929,.73248077], x, axis=0)
    y = lfilter([1,-2,1], [1,-1.99004745,.99007225], y, axis=0)
    return float(np.sum(y*y))


def process(x, profile):
    body, presence, top, tail_db = profile
    y = equalize(x, *body)
    y = equalize(y, *presence)
    y = equalize(y, *top, shelf=True)
    # Leave the transient in place. The taper starts relative to this take's own onset.
    level = np.max(abs(x), axis=1)
    onset = int(np.flatnonzero(level>level.max()*.035)[0])
    elapsed = (np.arange(len(x))-onset)/RATE
    tail = np.clip((elapsed-.085)/.135, 0, 1)
    return y * 10**((tail_db*tail*tail*(3-2*tail))/20)[:,None]


def main():
    receipt = []
    for gun, profile in PROFILES.items():
        takes = []
        for i in range(1, 2 if gun=="M24" else 5):
            if gun=="M24":
                donor = M24+"/S_M24_Suppressed"
                source = HERE.parent/"M24FireAudio20261104/S_M24_Suppressed.wav"
                target = donor+"_Warm"
            else:
                donor = f"/Game/Weapons/M4SuppressedAudio20260921/S_M4_Suppressed_{i:02d}"
                source = HERE.parent/"M4SuppressedAudio20260921"/(donor.split("/")[-1]+".wav")
                target = f"{BANK}/{gun}/S_{gun}_Suppressed_{i:02d}"
            x, fs = sf.read(source, always_2d=True)
            if fs!=RATE or x.shape[1]!=2:
                raise ValueError(f"Unexpected format for {source}")
            takes.append((source, donor, target, x, process(x, profile)))
        gain = np.sqrt(sum(exposure(x) for _,_,_,x,_ in takes)/sum(exposure(y) for _,_,_,_,y in takes))
        peak = max(np.max(abs(resample_poly(y,4,1,axis=0))) for _,_,_,_,y in takes)
        gain = min(gain, 10**(-1.0/20)/peak)
        for source, donor, target, x, y in takes:
            wav = HERE/(target.split("/")[-1]+".wav")
            y = gain*y
            sf.write(wav, y, RATE, subtype="PCM_16")
            receipt.append(dict(gun=gun, source=str(source.relative_to(HERE.parent)), donor=donor,
                                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                package=target, wav=wav.name, frames=len(y), pitch=1.0,
                                exposure_change_db=round(10*np.log10(exposure(y)/exposure(x)),2)))
    (HERE/"masters.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
