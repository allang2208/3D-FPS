import imageio_ffmpeg,subprocess
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/ue_export');src=Path('Y:/开发/游戏/素材库/怪物/手脑/声音')
for dst,name in [('slam','hitting.mp3'),('howl','howling.mp3'),('move','walking.mp3')]:
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-i',str(src/name),'-ac','1','-ar','44100','-c:a','pcm_s16le',str(out/(dst+'.wav'))],check=True)
