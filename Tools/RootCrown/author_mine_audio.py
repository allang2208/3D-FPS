"""Author a quiet planting texture without the old three timed impact bursts. No audition."""
from pathlib import Path
import json,wave
import numpy as np
root=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
out=root/'Audio/MinesV01';out.mkdir(parents=True,exist_ok=True)
rate=48000;t=np.arange(round(4.2*rate))/rate;rng=np.random.default_rng(141014)
def noise(width):return np.convolve(rng.normal(size=len(t)),np.ones(width)/width,mode='same')
envelope=np.clip(t/.5,0,1)*np.clip((2.65-t)/.8,0,1)
grain=(.65+.35*np.sin(t*8.5)**2)*noise(65)
tone=np.sin(2*np.pi*(33*t+1.2*t*t))*.045
y=(grain*.6+noise(9)*.045+tone)*envelope
y=y/max(1e-6,float(np.max(np.abs(y))))*.28
path=out/'RootCrown_MinePlant.wav'
with wave.open(str(path),'wb') as stream:
    stream.setparams((1,2,rate,len(y),'NONE','not compressed'));stream.writeframes((y*32767).astype('<i2').tobytes())
(root/'Reports/mine_audio_authoring.json').write_text(json.dumps({'file':str(path),'source':'original synthesis','sample_rate':rate,'seconds':4.2,'timed_explosion_impacts':False,'auditioned':False},indent=2),encoding='utf8')
print('ROOT_CROWN_MINE_AUDIO_AUTHORED')
