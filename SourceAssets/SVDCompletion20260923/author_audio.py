from pathlib import Path
import numpy as np,soundfile as sf,hashlib,json
from scipy.signal import butter,sosfilt,resample_poly
O=Path(__file__).parent;src=O.parent/'FirearmAudio20260913/Original';D=O/'Audio';D.mkdir(exist_ok=True);rate=48000
inputs=[('AK-47/C_29P.wav',1.070),('AK-47/C_29P.wav',5.612),('AR-15/D_24P.wav',.584),('AR-15/D_32P.wav',.706)];sources=[]
for i,(file,anchor) in enumerate(inputs):
 p=src/file;x,sr=sf.read(p,always_2d=True);x=x.mean(axis=1);lo=int((anchor-.13)*sr);hi=int((anchor+.015)*sr);local=np.abs(x[lo:hi]);start=lo+np.flatnonzero(local>local.max()*.12)[0]
 x=resample_poly(x[max(0,start-48):start+int(sr*.62)],rate,sr);x=np.pad(x,(0,max(0,int(rate*.62)-len(x))))[:int(rate*.62)];t=np.arange(len(x))/rate
 def band(lo,hi):return sosfilt(butter(2,[lo,hi],btype='bandpass',fs=rate,output='sos'),x)
 y=(.76*band(85,10000)+.42*band(85,650))*np.exp(-np.maximum(t-.085,0)/.15)
 y[:32]*=np.linspace(0,1,32);y[-1920:]*=np.linspace(1,0,1920);y*=.78/max(abs(y).max(),1e-8)
 name=f'S_SVD_Fire_{i+1:02d}';sf.write(D/(name+'.wav'),y,rate,subtype='PCM_16');sources.append({'asset':name,'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'onset_anchor':anchor})
(O/'audio_provenance.json').write_text(json.dumps({'license':'CC0-1.0','source_record':str(O.parent/'FirearmAudio20260913/provenance.json'),'description':'Designed rifle voices from Free Firearm library recordings; not an authentic SVD recording. Existing AKM mechanical cues retain their original provenance.','files':sources},indent=2));print('SVD_AUDIO_AUTHORED',len(sources))
