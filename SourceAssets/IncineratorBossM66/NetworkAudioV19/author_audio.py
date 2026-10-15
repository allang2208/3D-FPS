from pathlib import Path
import json,wave,hashlib
import numpy as np
from scipy.signal import butter,sosfilt
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/IncineratorBossM66/NetworkAudioV19';OUT=ROOT/'Audio';OUT.mkdir(parents=True,exist_ok=True)
SR=48000
def read(path):
    with wave.open(str(path),'rb') as w:
        rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth()
        if width!=2:raise RuntimeError('Expected PCM16 source '+str(path))
        y=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float).reshape(-1,channels).mean(axis=1)/32768.
    if rate!=SR:y=np.interp(np.arange(round(len(y)*SR/rate))*rate/SR,np.arange(len(y)),y)
    return y
def fade(y,a=.008,b=.06):
    t=np.arange(len(y))/SR;return y*np.minimum(1,t/a)*np.clip((len(y)/SR-t)/b,0,1)
base=P/'SourceAssets/BellowSacLobberMeshy20261012'
rows={
 'FootLeft':(base/'StepsHurtV11/Audio/S_Bellow_FootstepA.wav',0,None,.88,.65),
 'FootRight':(base/'StepsHurtV11/Audio/S_Bellow_FootstepC.wav',0,None,.88,.65),
 'Hurt':(base/'StepsHurtV11/Audio/S_Bellow_HurtA.wav',0,None,.88,.60),
 'Death':(base/'CreatureAudioV10/Audio/S_Bellow_DeathA.wav',0,None,.83,.75),
 'Land':(base/'CreatureAudioV10/Audio/S_Bellow_BodyFall.wav',0,None,.82,.80),
 'SweepImpact':(base/'CreatureAudioV10/Audio/S_Bellow_BodyFall.wav',0,.25,1.05,.60),
 'SweepSwing':(P/'SourceAssets/HangingBellM09Meshy20261003/MotionV04/Audio/S_M09_Claw.wav',0,.52,.92,.63),
 'SlamImpact':(P/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV22/Audio/S_M14_TrunkSlam_v22.wav',.54,1.40,.88,.88),
 'BackSmoke':(P/'SourceAssets/M10ChenXia20261003/AudioV1/Wav/S_M10_Gas.wav',2,5,.92,.38),
 'Recover':(P/'SourceAssets/IncineratorBossM66/FurnaceBreathV17/Export/M66_furnace_inhale.wav',.15,1.15,.95,.38)}
manifest={'sample_rate':SR,'clips':{},'source_policy':'Existing M-series authored sounds; preserve original CC0/provenance records. No external downloads.','auditioned':False}
for role,(src,start,end,speed,gain) in rows.items():
    y=read(src);y=y[round(start*SR):round(end*SR) if end else len(y)]
    if role=='Recover':y=y[::-1]
    y=np.interp(np.arange(round(len(y)/speed))*speed,np.arange(len(y)),y)
    y=sosfilt(butter(2,[40,6000 if role!='BackSmoke' else 1700],btype='bandpass',fs=SR,output='sos'),y)
    if role=='BackSmoke':
        n=round(.16*SR);t=np.linspace(0,1,n);join=y[-n:]*(1-t)+y[:n]*t;y=np.concatenate([join,y[n:-n]])
    else:y=fade(y)
    peak=float(np.max(np.abs(y)));y=y/max(peak,1e-8)*gain
    path=OUT/('S_M66_'+role+'_V19.wav')
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(np.rint(y*32767).astype('<i2').tobytes())
    manifest['clips'][role]={'file':str(path),'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_slice':[start,end],'speed':speed,'duration':len(y)/SR,'loop':role=='BackSmoke','peak':float(np.max(np.abs(y)))}
(ROOT/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v['duration'] for k,v in manifest['clips'].items()}))
