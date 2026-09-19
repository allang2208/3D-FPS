from pathlib import Path
import numpy as np
import soundfile as sf

root = Path(__file__).resolve().parent
source = root.parent/'M4HK416AudioEmpty20260909/Audio/fire.wav'
x, rate = sf.read(source, always_2d=True)
out = root/'M4OriginalVariants'
out.mkdir(exist_ok=True)
t = np.arange(len(x))/rate
# Keep the original attack, pitch and peak level. Only vary the late decay slightly.
blend = np.clip((t-.09)/.10,0,1)
for i, gain in enumerate([1.0,.94,1.04,.97],1):
    y = x * (1+(gain-1)*blend[:,None])
    sf.write(out/f'S_M4_Original_{i:02d}.wav', np.clip(y,-1,1),rate,subtype='PCM_16')
print('Authored four original M4 variations; attack and pitch preserved.')
