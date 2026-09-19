from pathlib import Path
import shutil
import numpy as np
import soundfile as sf

root = Path(__file__).resolve().parent/'QBZ95Selected'
root.mkdir(exist_ok=True)
source = Path('Y:/开发/游戏/素材库/音效/开枪音效/qbz95/fire.mp3')
shutil.copy2(source, root/'fire.mp3')
x, rate = sf.read(root/'fire.mp3', always_2d=True)
t = np.arange(len(x))/rate
blend = np.clip((t-.09)/.10,0,1)
for i, gain in enumerate([1.0,.94,1.04,.97],1):
    y = x * (1+(gain-1)*blend[:,None])
    sf.write(root/f'S_QBZ191_Selected_{i:02d}.wav',np.clip(y,-1,1),rate,subtype='PCM_16')
print('QBZ95 source converted with four subtle tail variations.')
