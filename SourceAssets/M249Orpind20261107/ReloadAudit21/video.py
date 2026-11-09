from pathlib import Path
import json,subprocess,numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
r=Path(__file__).resolve().parent;root=r/'release';out=r/'Preview';out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','20','-i','-','-an','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'M249_reload_review.mp4')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
labels=[]
for mag in ['box','30','45']:
 for empty in [False,True]:
  name=f'{mag}_{"empty" if empty else "normal"}_base_player';folder=(r/'delivery_final' if mag=='box' else root)/name;j=json.loads((folder/'review.json').read_text());title=f'M249 {"原厂弹箱" if mag=="box" else mag+" 发侧弹匣"} · {"空仓换弹" if empty else "普通换弹"}'
  for f in j['frames']:
   im=Image.open(folder/f['file']).convert('RGB');draw=ImageDraw.Draw(im);draw.rectangle((0,0,960,62),fill=(18,23,30));draw.text((14,7),title,font=font,fill=(235,238,242));draw.text((14,36),f"UE 后台动作检查 · 运行 {f['runtime']:.2f}s / 动作源 {f['source']:.2f}s · 静音",font=small,fill=(166,179,194));p.stdin.write(np.asarray(im).tobytes())
  labels.append(dict(case=name,frames=len(j['frames']),duration=j['duration']))
p.stdin.close();code=p.wait()
if code:raise RuntimeError(code)
(out/'manifest.json').write_text(json.dumps(dict(source='delivery_final box + release side magazines',fps=20,audio=False,cases=labels),indent=2));print('RELOAD_REVIEW_VIDEO_SAVED',flush=True)
