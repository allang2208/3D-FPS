"""Produce a cosmetic suppressed cue from SUPER90's current accepted fire source."""
from pathlib import Path
import hashlib,json
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfilt
O=Path(__file__).parent
source=O.parent/'Super90GameDevAudio20261007/Wav/S_Super90_Fire.wav'
prior=json.loads((O.parent/'Super90GameDevAudio20261007/provenance.json').read_text(encoding='utf-8'))
x,rate=sf.read(source,always_2d=True,dtype='float64')
t=np.arange(len(x))/rate
def filt(data,kind,freq):return sosfilt(butter(2,freq,fs=rate,btype=kind,output='sos'),data,axis=0)
clean=filt(x,'highpass',65)
core=filt(clean,'lowpass',2900)
body=filt(clean,'bandpass',[100,260])
box=filt(clean,'bandpass',[400,900])
detail=filt(clean,'bandpass',[2600,7000])
y=(.88*core+.10*body-.16*box)*np.exp(-np.maximum(t-.065,0)/.12)[:,None]
y+=.10*detail*np.exp(-t/.07)[:,None]
# Retain pitch/channel/timing; set the authored attack below the normal cue.
window=round(.100*rate)
rms=lambda v:float(np.sqrt(np.mean(v*v)))
gain=(rms(x[:window])*10**(-6/20))/max(rms(y[:window]),1e-12)
y*=gain
peak=float(np.abs(y).max());y*=min(1.,10**(-1.5/20)/max(peak,1e-12))
fade=round(.015*rate);y[-fade:]*=np.linspace(1,0,fade)[:,None]
y[:16]*=np.linspace(0,1,16)[:,None]
dest=O/'Audio/S_Super90_Suppressed.wav';dest.parent.mkdir(exist_ok=True)
sf.write(dest,y,rate,subtype='PCM_24')
receipt={'revision':'Super90SuppressedV1_20261015','source':str(source),
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'output':str(dest),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
    'normal_asset':prior['audio']['Fire']['asset'],
    'asset':'/Game/Weapons/CommonShotgun/Suppressor20261015/Audio/S_Super90_Suppressed',
    'sample_rate':rate,'channels':x.shape[1],'duration_seconds':len(y)/rate,
    'processing':'Filtered source body, restrained crack, shortened tail; original pitch and duration',
    'attack_100ms_rms_delta_db':20*np.log10(rms(y[:window])/rms(x[:window])),
    'license_note':prior['license_note'],'recording_type':'Designed game cue, not a recording of a real suppressed shotgun',
    'auditioned':False,'runtime_tested':False}
(O/'audio_provenance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('SUPER90_SUPPRESSED_AUDIO_AUTHORED')
