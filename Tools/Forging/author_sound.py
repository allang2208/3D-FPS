"""Use the user-supplied strike recording; retain the old synthetic fallback."""
import math,random,struct,wave,subprocess
from pathlib import Path
out=Path(__file__).resolve().parents[2]/'SourceAssets/ForgeInteraction20260927/ForgeHammerImpact.wav'
recording=out.parent/'AudioSource'/'ForgeHammerImpact.mp3'
if recording.exists():
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error',
                    '-i',str(recording),'-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',str(out)],check=True)
    print('FORGE_SOUND_CONVERTED',out)
    raise SystemExit(0)
random.seed(2709);rate=48000;samples=[];smooth=0
for i in range(int(rate*.85)):
    t=i/rate;n=random.uniform(-1,1);smooth=.72*smooth+.28*n
    value=.36*(n-smooth)*math.exp(-t*190)+.12*smooth*math.exp(-t*36)
    for f,a,decay in [(785,.26,11),(1284,.20,8),(2177,.13,14),(3561,.09,19),(5209,.05,28)]:
        value+=a*math.sin(math.tau*f*t)*math.exp(-t*decay)
    value*=min(1,t/.0006);samples.append(struct.pack('<h',int(max(-.95,min(.95,value))*32767)))
with wave.open(str(out),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(samples))
print('FORGE_SOUND_AUTHORED',out)
