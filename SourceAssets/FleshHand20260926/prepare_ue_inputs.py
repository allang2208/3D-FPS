"""Pack Meshy PBR channels and transcode the original attack sound for UE."""
from pathlib import Path
import json,shutil,subprocess
import numpy as np
from PIL import Image
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'Meshy/candidate01/downloads'
OUT=ROOT/'UEInputs';OUT.mkdir(exist_ok=True)
shutil.copy2(SRC/'texture_0.png',OUT/'BaseColor.png')
shutil.copy2(SRC/'texture_0_normal.png',OUT/'Normal.png')
rough=Image.open(SRC/'texture_0_roughness.png').convert('L')
metal=Image.open(SRC/'texture_0_metallic.png').convert('L').resize(rough.size)
Image.merge('RGB',(Image.new('L',rough.size,255),rough,metal)).save(OUT/'ORM.png')
# Skin / sparse wetness / scab. No copied Mutant3 UV-space masks.
r=np.asarray(rough.resize((1024,1024))).astype(np.float32)/255
mask=np.zeros((1024,1024,3),dtype=np.uint8);mask[:,:,0]=255
mask[:,:,1]=(np.clip((.4-r)*.6,0,.12)*255).astype(np.uint8)
Image.fromarray(mask).save(OUT/'TissueMasks.png')
sound=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/enemies/flyhand/hitting-2.mp3')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-i',str(sound),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(OUT/'S_FleshHand_Impact.wav')],check=True)
(OUT/'sources.json').write_text(json.dumps({'pbr_source':str(SRC),'normal_convention':'OpenGL; flip green at UE import',
 'ORM':'R=constant AO 1; G=Meshy roughness; B=Meshy metallic','TissueMasks':'R=skin; G=restrained roughness-derived wetness; B=no scab',
 'audio_source':str(sound),'audio_format':'mono PCM16 48kHz','license':'original project provenance retained; no public redistribution claim'},ensure_ascii=False,indent=2),encoding='utf-8')
print('FLESHHAND_UE_INPUTS_SAVED')
