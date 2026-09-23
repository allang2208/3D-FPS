"""Cut the supplied video into independently timed PKM pull/push sounds."""
import hashlib,json,math,subprocess,wave
from pathlib import Path
import numpy as np

O=Path(__file__).parent;R=O.parent;RATE=48000
SOURCE=R/'References/PKM_UserReloadReference.mp4'
FFMPEG=R.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
def run(*args):subprocess.run([str(FFMPEG),'-v','error','-y',*map(str,args)],check=True)
def read(path):
    with wave.open(str(path),'rb') as f:
        return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float64)/32768
def write(path,x):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes(np.round(np.clip(x,-1,1-1/32768)*32768).astype('<i2').tobytes())
def tempo_filters(speed):
    values=[]
    while speed>2:values.append(2.);speed/=2
    while speed<.5:values.append(.5);speed/=.5
    values.append(speed)
    return ','.join(f'atempo={v:.9f}' for v in values)

run('-i',SOURCE,'-vn','-ar',RATE,'-ac',1,'-af','highpass=f=80','-c:a','pcm_s16le',O/'reference_filtered.wav')
x=read(O/'reference_filtered.wav')
# Movement beds use the visible hand travel; the two dominant original clicks
# near 24.73 / 25.03 s belong to the rear and forward stops respectively.
specs=[('ChargePullMove',24.180,24.710,5.13,.23,'ChargePull'),
       ('ChargeRearStop',24.710,24.905,5.36,None,'ChargePull'),
       ('ChargePushMove',24.905,25.010,5.48,.34,'ChargeRelease'),
       ('ChargeFrontStop',25.010,25.225,5.82,None,'ChargeRelease')]
clips=[]
for name,a,b,event,duration,reference in specs:
    y=x[round(a*RATE):round(b*RATE)].copy();onset=0;tempo=1.
    if duration is not None:
        # Pitch-preserving stretch only on quiet movement, not the metal click.
        raw=O/(name+'_cut.wav');processed=O/(name+'_tempo.wav');write(raw,y)
        tempo=(b-a)/duration
        run('-i',raw,'-af',tempo_filters(tempo)+f',apad,atrim=duration={duration}',
            '-c:a','pcm_s16le',processed)
        y=read(processed)
    else:
        # Trim the lead-in to the first substantial transient; align the attack
        # to the mechanical stop instead of scheduling the file's silent prefix.
        block=round(.001*RATE)
        energies=np.array([np.sqrt(np.mean(y[i:i+block]**2)) for i in range(0,len(y)-block,block)])
        peak=int(np.argmax(energies));hits=np.flatnonzero(energies[:peak+1]>=energies[peak]*.25)
        onset=max(0,int(hits[0])*block-round(.001*RATE));y=y[onset:]
    fade_in=min(round((.003 if duration else .001)*RATE),len(y))
    fade_out=min(round((.018 if duration else .025)*RATE),len(y))
    y[:fade_in]*=np.linspace(0,1,fade_in);y[-fade_out:]*=np.linspace(1,0,fade_out)
    clips.append((name,y,a,b,event,tempo,reference,onset))
gain=10**(-4/20)/max(float(np.max(np.abs(row[1]))) for row in clips)
manifest={'source_url':'https://www.bilibili.com/video/BV1jHeA6sEmj/',
    'source_file':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'rights':'User-provided game-video reference; source recording and derivatives retained locally; redistribution rights not established.',
    'processing':'Video original mix, mono 48 kHz PCM16; 80 Hz highpass; movement only stretched without pitch change; stop attacks trimmed to onset; fades; shared -4 dBFS set peak.',
    'common_gain_db':20*math.log10(gain),'contacts':[]}
for name,y,a,b,event,tempo,reference,onset in clips:
    asset='S_PKM_'+name;wav=O/(asset+'.wav');write(wav,y*gain)
    manifest['contacts'].append({'name':name,'asset_name':asset,'wav':wav.name,'video_start':a,'video_end':b,
        'trim_lead_seconds':onset/RATE,'empty_source_time':event,'duration':len(y)/RATE,'tempo':tempo,
        'settings_reference':'/Game/Weapons/PKMLowpoly20260922/ReloadAudio22/S_PKM_'+reference,
        'wav_sha256':hashlib.sha256(wav.read_bytes()).hexdigest()})
(O/'audio_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'clips':len(clips),'contacts':[{k:r[k] for k in ('name','empty_source_time','duration','trim_lead_seconds')} for r in manifest['contacts']]}))
