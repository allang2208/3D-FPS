"""Prepare game texture inputs and a CC0-derived designed G18 sound bank."""
from pathlib import Path
import json,hashlib,wave,shutil,audioop
import numpy as np
from PIL import Image
O=Path(__file__).parent;T=O/'Textures';A=O/'Audio';T.mkdir(exist_ok=True);A.mkdir(exist_ok=True)
record={'textures':{},'audio':{}}
for source in (O/'Original/G18/G18/Textures_4K').glob('*.png'):
    if 'Height' in source.name:continue
    im=Image.open(source);original=im.size
    if max(im.size)>4096:im.thumbnail((4096,4096),Image.Resampling.LANCZOS)
    if any(n in source.name for n in ('Roughness','Metallic')):im=im.convert('L')
    path=T/('T_G18_'+source.name.removeprefix('g18_'));im.save(path)
    record['textures'][path.stem]={'source':str(source),'source_size':original,'size':im.size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
source=O.parent/'M1911Integration20260913/Audio/Source/1911_A_34P.wav'
with wave.open(str(source),'rb') as w:
    sr=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();raw=w.readframes(w.getnframes())
if width!=2:raw=audioop.lin2lin(raw,width,2)
x=np.frombuffer(raw,dtype='<i2').astype(np.float64).reshape(-1,channels).mean(axis=1)/32768
peak=np.max(np.abs(x));start=max(0,int(np.argmax(np.abs(x)>peak*.3))-int(.001*sr));x=x[start:]
def save(name,y):
    y=y[:int(.28*sr)]
    y*=np.minimum(1,np.arange(len(y))/max(1,.0002*sr))*np.minimum(1,np.arange(len(y))[::-1]/max(1,.012*sr))
    y*=.80/max(.001,np.max(np.abs(y)))
    with wave.open(str(A/(name+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((y*32767).astype('<i2').tobytes())
for i,ratio in enumerate((1.08,1.11,1.06,1.09),1):
    n=int(.28*sr);t=np.arange(n)/sr;y=np.interp(np.arange(n)*ratio,np.arange(len(x)),x,right=0)
    low=np.convolve(y,np.ones(29)/29,mode='same');y=(y-.32*low)*np.exp(-t*7.0)
    save(f'S_G18_Fire_{i:02}',y.copy())
    muted=np.convolve(y,np.ones(19)/19,mode='same');save(f'S_G18_Suppressed_{i:02}',.82*muted+.18*y)
shutil.copy2(A/'S_G18_Fire_01.wav',A/'S_G18_Fire.wav');shutil.copy2(A/'S_G18_Suppressed_01.wav',A/'S_G18_Suppressed.wav')
record['audio']={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_license':'CC0-1.0','source_url':'https://opengameart.org/content/the-free-firearm-sound-library','description':'Designed G18 game sound from CC0 1911 transient; not a real G18 recording','variants':4,'format':f'{sr} Hz mono PCM16','processing':'Onset trim, spectral shaping, short tail envelope, slight variant resampling; suppressor low-pass design','listened':False}
(O/'media_sources.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('G18 media authored')
