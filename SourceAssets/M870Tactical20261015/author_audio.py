"""Create M870's local sound bank from user-selected project inputs and their separate provenance."""
from pathlib import Path
import wave,json,shutil,hashlib
import numpy as np
from scipy.signal import resample_poly
O=Path(__file__).parent;P=O.parents[1];out=O/'Audio';out.mkdir(exist_ok=True)
fire=P/'SourceAssets/ShotgunAudioSwap20261017/Audio/S_M870_Fire.wav'
fire_provenance=json.loads((P/'SourceAssets/ShotgunAudioSwap20261017/provenance.json').read_text(encoding='utf-8'))['normal']
shutil.copy2(fire,out/'S_M870_Fire.wav')
reload=P/'SourceAssets/Super90GameDevAudio20261007/Wav/S_Super90_Reload.wav'
shutil.copy2(reload,out/'S_M870_Reload.wav')
bolt=P/'SourceAssets/Super90GameDevAudio20261007/Wav/S_Super90_Bolt.wav'
with wave.open(str(bolt),'rb') as w:
 rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();raw=w.readframes(w.getnframes())
if width!=2:raise RuntimeError('Expected retained PCM16 mechanical source')
x=np.frombuffer(raw,'<i2').astype(np.float64).reshape(-1,channels).mean(axis=1)/32768
cuts=[]
for role,lo,hi in [('PumpPull',0,.5),('PumpPush',.5,1.)]:
 a,b=int(lo*rate),min(len(x),int(hi*rate));window=max(1,int(.015*rate))
 energy=np.convolve(x[a:b]**2,np.ones(window)/window,'same');peak=a+int(np.argmax(energy));begin=min(max(a,peak-int(.035*rate)),b-int(.23*rate));end=min(b,begin+int(.23*rate));v=x[begin:end].copy()
 if len(v)<rate*.08:raise RuntimeError('Mechanical contact source is too short')
 v-=v.mean();v=resample_poly(v,160,147) if rate==44100 else v
 sr=48000 if rate==44100 else rate;edge=min(int(.004*sr),len(v)//4);v[:edge]*=np.linspace(0,1,edge);v[-edge:]*=np.linspace(1,0,edge)
 v*=min(2.,.72/max(abs(v).max(),1e-6));dest=out/f'S_M870_{role}.wav'
 with wave.open(str(dest),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(np.clip(v*32767,-32768,32767).astype('<i2').tobytes())
 cuts.append(dict(role=role,source=str(bolt),begin=begin/rate,end=end/rate))
shutil.copy2(out/'S_M870_PumpPull.wav',out/'S_M870_Equip.wav')
report=dict(fire=fire_provenance,mechanical=dict(source_provenance=str(P/'SourceAssets/Super90GameDevAudio20261007/provenance.json'),cuts=cuts,note='Project-retained mechanical and shell insertion audio; its provenance is independent of the Sketchfab model and selected fire sound'),auditioned=False,outputs={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('*.wav')})
(O/'audio_provenance.json').write_text(json.dumps(report,indent=2));print('M870_AUDIO_AUTHORED',len(report['outputs']))
