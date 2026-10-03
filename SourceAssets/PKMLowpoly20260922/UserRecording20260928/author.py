from pathlib import Path
import json,numpy as np,soundfile as sf,hashlib
P=Path(__file__).resolve().parent
x,sr=sf.read(P/'recording.wav')
cuts=[('CoverOpen',8.285,8.75,'ReloadAudio22'),('BeltLift',8.89,9.46,'ReloadAudio22'),('BoxOut',9.79,10.24,'ReloadAudio22'),('BoxInsert',11.16,11.53,'ReloadAudio22'),('BeltSeat',11.59,12.30,'ReloadAudio22'),('CoverClose',12.91,13.15,'ReloadAudio22'),('ChargePullMove',13.69,13.83,'ChargeAudio35'),('ChargeRearStop',13.83,13.99,'ChargeAudio35'),('ChargePushMove',14.00,14.14,'ChargeAudio35'),('ChargeFrontStop',14.14,14.38,'ChargeAudio35')]
rows=[]
for name,a,b,folder in cuts:
 y=x[round(a*sr):round(b*sr)].copy(); n=round(.003*sr); m=round(.012*sr)
 y[:n]*=np.linspace(0,1,n)[:,None];y[-m:]*=np.linspace(1,0,m)[:,None]
 wav='S_PKM_'+name+'.wav';sf.write(P/wav,y,sr,subtype='PCM_16')
 rows.append(dict(name='S_PKM_'+name,start=a,end=b,folder=folder,wav=wav))
(P/'cuts.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('Authored',len(rows),'stereo 48 kHz PCM contacts; original gain retained; 3/12 ms edge fades only.')
