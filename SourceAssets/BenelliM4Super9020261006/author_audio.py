import wave,numpy as np,json,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O/'Audio';p=R/'Mossberg_N_26P.wav'
with wave.open(str(p),'rb') as w:
 sr=w.getframerate();ch=w.getnchannels();raw=w.readframes(w.getnframes())
a=np.frombuffer(raw,np.uint8).reshape(-1,3);v=a[:,0].astype(np.int32)+(a[:,1].astype(np.int32)<<8)+(a[:,2].astype(np.int32)<<16);v=np.where(v>=1<<23,v-(1<<24),v)/(1<<23);v=v.reshape(-1,ch).mean(axis=1)
k=np.arange(-24,25);fir=np.sinc(k*.46)*np.hanning(49);fir/=fir.sum()
files=[]
for i,peak in enumerate([.785,4.575,7.945],1):
 start=int((peak-.025)*sr);x=v[start:start+int(1.1*sr)].copy();x=np.convolve(x,fir,'same')[::2];x-=np.mean(x);x*=.85/max(np.max(abs(x)),1e-6);x[:48]*=np.linspace(0,1,48);x[-4800:]*=np.linspace(1,0,4800)
 file=R/f'S_Super90_Fire_{i:02}.wav'
 with wave.open(str(file),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes((x*32767).astype('<i2').tobytes())
 files.append({'file':str(file),'source_start':start/sr})
(R/'provenance.json').write_text(json.dumps({'license':'CC0-1.0','authors':['Ben Jaszczak','Brian Nelson','Kevin Heras','Matthew Nanney'],'source_page':'https://opengameart.org/content/the-free-firearm-sound-library','source_file':'Mossberg/N_26P.wav','note':'Mossberg shotgun recording used as Super90 game audio; not a Benelli-specific field recording.','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'outputs':files},indent=2))
