"""Decode the user's existing video for event-level sound authoring."""
from pathlib import Path
import subprocess,json,hashlib
import numpy as np,soundfile as sf,imageio_ffmpeg
from scipy.signal import butter,sosfiltfilt,find_peaks
O=Path(__file__).parent;R=O.parent
source=R/'References/PKM_UserReloadReference.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-vn','-ar','48000','-ac','1','-c:a','pcm_s24le',str(O/'reference_audio.wav')],check=True)
x,rate=sf.read(O/'reference_audio.wav');filtered=sosfiltfilt(butter(3,180,fs=rate,btype='highpass',output='sos'),x)
step=int(rate*.005);energy=np.array([np.sqrt(np.mean(filtered[i:i+step]**2)) for i in range(0,len(x)-step,step)])
rows=[]
for a,b in [(10.2,16.8),(23.3,26.4)]:
 segment=energy[int(a/.005):int(b/.005)]
 peaks,_=find_peaks(segment,distance=14,prominence=.006)
 rows.append({'range':[a,b],'peaks':[{'time':round(a+p*.005,3),'rms':round(float(segment[p]),4)} for p in peaks]})
(O/'reference_events.json').write_text(json.dumps({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'sample_rate':rate,'duration':len(x)/rate,'event_envelopes':rows},indent=2))
print(json.dumps(rows),flush=True)
