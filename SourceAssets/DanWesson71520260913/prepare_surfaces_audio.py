"""Convert Unity smoothness to UE ORM; author licensed revolver audio cues."""
import json, urllib.request, urllib.parse, wave, shutil
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
from PIL import Image, ImageOps
O=Path(__file__).parent
icons=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
shutil.copy2(icons/'trigger_m1911_lightweight_fast.png',icons/'trigger_dw715_lightweight_fast.png')
(O/'Textures').mkdir(exist_ok=True);(O/'Audio').mkdir(exist_ok=True);(O/'Audio/Original').mkdir(exist_ok=True)
base=next((O/'Original').rglob('Base Set Semi Dmg'))
albedo=Image.open(base/'DW_Set0_SemiDmg_AlbedoTransparency.png').convert('RGB');albedo.save(O/'Textures/T_DW715_BaseColor.png')
metal=Image.open(base/'DW_Set0_SemiDmg_MetallicSmoothness.png').convert('RGBA')
ao=Image.open(base/'DW_Set0_SemiDmg_AO.png').convert('L')
Image.merge('RGB',(ao,ImageOps.invert(metal.getchannel('A')),metal.getchannel('R'))).save(O/'Textures/T_DW715_ORM.png')
Image.open(base/'DW_Set0_SemiDmg_Normal.png').convert('RGB').save(O/'Textures/T_DW715_Normal.png')
source_path='sfx/firearm_sfx/Prepared SFX Library/Smith & Wesson 642/V_22P.wav'
url='https://raw.githubusercontent.com/petroulacl/fps-asset-kit/a19b7458a593598211c95ec46ef4eb4b6d1f94d7/'+urllib.parse.quote(source_path)
original=O/'Audio/Original/SW642_V_22P.wav'
if not original.exists():
    with urllib.request.urlopen(url,timeout=45) as response:original.write_bytes(response.read())
x,rate=sf.read(original,always_2d=True);x=x.mean(axis=1)
window=max(1,rate//1000);envelope=np.array([np.max(np.abs(x[n:n+window])) for n in range(0,len(x),window)])
start=max(0,int(np.flatnonzero(envelope>envelope.max()*.45)[0])*window-int(rate*.002))
shot=resample_poly(x[start:start+int(rate*.85)],48000,rate);time=np.arange(len(shot))/48000
shot=sosfilt(butter(2,[95,12500],btype='bandpass',fs=48000,output='sos'),shot)
shot*=np.exp(-np.maximum(time-.1,0)/.28);shot*=.84/max(abs(shot));shot[-1200:]*=np.linspace(1,0,1200)
sf.write(O/'Audio/S_DW715_Fire.wav',shot,48000,subtype='PCM_16')
# Newly synthesized mechanism sounds: metallic catches, extractor rattle,
# loader seating and closed-crane latch. No commercial-game audio is used.
rng=np.random.default_rng(715)
def click(name,length,pulses,gain):
    t=np.arange(int(length*48000))/48000;y=np.zeros_like(t)
    for at,frequency,level in pulses:
        dt=np.maximum(0,t-at);active=(t>=at)
        y+=level*active*(np.sin(2*np.pi*frequency*dt)*np.exp(-dt/0.014)+.45*rng.normal(size=len(t))*np.exp(-dt/.007))
    y*=gain/max(.001,max(abs(y)));y[-min(240,len(y)):]*=np.linspace(1,0,min(240,len(y)))
    sf.write(O/f'Audio/S_DW715_{name}.wav',y,48000,subtype='PCM_16')
click('MagOut',.16,[(0,1500,1),(.032,850,.7)],.40)
click('ChargePull',.30,[(0,1200,1)]+[(.026+i*.022,2600+i*240,.65) for i in range(6)],.36)
click('MagInsert',.20,[(0,1200,.5),(.024,2400,.8),(.053,1700,.55)],.35)
click('MagSeat',.17,[(0,970,1),(.038,1800,.5)],.38)
click('ChargeRelease',.18,[(0,660,1),(.016,1900,.7),(.035,3300,.3)],.48)
click('DryClick',.1,[(0,2100,1)],.25)
click('Equip',.20,[(0,380,.5),(.066,790,.3)],.20)
(O/'Audio/provenance.json').write_text(json.dumps({'source_page':'https://opengameart.org/content/the-free-firearm-sound-library','source_file':source_path,'download':url,'license':'CC0-1.0','authors':['Ben Jaszczak','Brian Nelson','Kevin Heras','Matthew Nanney'],'fire':'Designed from S&W 642 revolver recording; not a recording of an actual 715','offset_seconds':start/rate,'mechanics':'Original deterministic synthesis in this script','listening_test':False},indent=2))
print('DW715_TEXTURES_AUDIO_AUTHORED')
