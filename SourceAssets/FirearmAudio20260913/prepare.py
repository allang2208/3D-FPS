"""Reproducible, recording-derived first-person rifle voices (CC0 sources)."""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
RATE = 48000
OUT = ROOT / 'Wav'
OUT.mkdir(exist_ok=True)

def band(x, low, high):
    return sosfilt(butter(2, [low, high], btype='bandpass', fs=RATE, output='sos'), x)

def shot(file, anchor):
    x, rate = sf.read(ROOT / 'Original' / file, always_2d=True)
    # Locate the attack before the listed peak, not at the clipped peak itself.
    x = x.mean(axis=1)
    lo, hi = int((anchor-.13)*rate), int((anchor+.015)*rate)
    local = np.abs(x[lo:hi])
    onset = lo + np.flatnonzero(local > max(local)*.12)[0]
    x = x[max(0,onset-int(rate*.001)):onset+int(rate*.56)]
    x = resample_poly(x, RATE, rate)
    return np.pad(x, (0,max(0,int(RATE*.56)-len(x))))[:int(RATE*.56)]

ar = [('AR-15/D_24P.wav', .584), ('AR-15/D_24P.wav', 3.939),
      ('AR-15/D_32P.wav', .706), ('AR-15/D_32P.wav', 5.650)]
ak = [('AK-47/C_29P.wav', 1.070), ('AK-47/C_29P.wav', 5.612)]
manifest = {'source_page':'https://opengameart.org/content/the-free-firearm-sound-library',
 'license':'CC0-1.0', 'authors':['Ben Jaszczak','Brian Nelson','Kevin Heras','Matthew Nanney'],
 'mirror':'https://github.com/petroulacl/fps-asset-kit/tree/main/sfx/firearm_sfx',
 'note':'QBZ191 and suppressed voices are designed composites, not model-specific field recordings.',
 'sources':[], 'outputs':[]}
for p in sorted((ROOT/'Original').rglob('*.wav')):
    manifest['sources'].append({'file':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for weapon in ['M4','QBZ191']:
    for i, (file, anchor) in enumerate(ar):
        x = shot(file, anchor)
        t = np.arange(len(x))/RATE
        # Retain a compact real outdoor return, attenuating its accumulation in bursts.
        envelope = np.exp(-np.maximum(t-.065,0)/.105)
        envelope[-int(RATE*.04):] *= np.linspace(1,0,int(RATE*.04))
        if weapon == 'M4':
            normal = (.84*band(x,110,11000)+.28*band(x,140,650))*envelope
        else:
            body = shot(*ak[i%2])
            normal = (.70*band(x,170,8700)+.38*band(body,130,1500)*np.exp(-t/.065))*envelope
        normal[:24] *= np.linspace(0,1,24)
        normal *= .70/max(np.max(np.abs(normal)),1e-8)
        # A restrained suppressed design from the same recording, no third-party layers.
        suppressed = band(normal,190,3300) * np.exp(-t/.12)
        suppressed *= .32/max(np.max(np.abs(suppressed)),1e-8)
        for mode, data in [('Fire',normal),('Suppressed',suppressed)]:
            name = f'S_{weapon}_{mode}_{i+1:02d}'
            sf.write(OUT/(name+'.wav'),data,RATE,subtype='PCM_16')
            manifest['outputs'].append({'asset':name,'ar_source':file,'peak_anchor_seconds':anchor,
              'body_source':ak[i%2] if weapon=='QBZ191' else None})
(ROOT/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Authored 16 rifle voices at 48 kHz; no playback testing performed.')
