import re,json,subprocess,bisect,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
from datetime import datetime
parser=argparse.ArgumentParser();parser.add_argument('--run',default='akm-native-v2');parser.add_argument('--redwood',action='store_true');parser.add_argument('--source-matched',action='store_true');parser.add_argument('--equip-only',action='store_true');parser.add_argument('--soviet',action='store_true');args=parser.parse_args()
O=Path(__file__).parent;run=O.parents[1]/'Saved/AKMIntegrationAudit'/args.run;out=O/('Redwood/Delivery' if args.redwood else 'Native/Delivery');out.mkdir(parents=True,exist_ok=True)
if args.source_matched:out=O/'SourceMatched/Delivery';out.mkdir(parents=True,exist_ok=True)
if args.equip_only:out=O/'EquipCharge/Delivery';out.mkdir(parents=True,exist_ok=True)
if args.soviet:out=O.parent/'AKMSoviet20260911/Delivery';out.mkdir(parents=True,exist_ok=True)
log=(O/f'runtime-{args.run}.log').read_text(encoding='utf-8-sig',errors='replace')
caption='AKM | M4 金属与手模 + 免费木纹红木色 | 实际游戏画面与录音' if args.redwood else 'AKM 原生 M4 手模候选 | 原版贴图未取得 | 实际游戏画面与录音'
if args.source_matched:caption='AKM | Fab / Quixel 金属表面 + 原动作适配 M4 手模 | 实机与录音'
if args.equip_only:caption='AKM 装备 | 弹匣固定、左手持枪、右手拉栓 | 实机与录音'
if args.soviet:caption='AKM | Soviet Assault Rifle 原配 PBR + 现有手模与动画 | 实机与录音'
rows=[]
def stamp(t):return datetime.strptime(t,'%Y.%m.%d-%H.%M.%S:%f').timestamp()
for wall,stage,index,t in re.findall(r'\[([\d.:-]+)\]\[\s*\d+\].*?AKM_FRAME stage=(\d+) index=(\d+) elapsed=([\d.]+)',log):
 p=run/('frame_%04d.png'%int(index))
 if p.exists():rows.append((stamp(wall),p,int(stage)))
if args.equip_only:rows=[r for r in rows if r[2]==8]
assert rows
times=[r[0] for r in rows];start=times[0];duration=times[-1]-start;fps=30
ff=imageio_ffmpeg.get_ffmpeg_exe();silent=out/'AKM_native_candidate_silent.mp4'
proc=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x580','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for k in range(round(duration*fps)):
 row=rows[max(0,bisect.bisect_right(times,start+k/fps)-1)];im=Image.new('RGB',(960,580),(20,24,30));im.paste(Image.open(row[1]).convert('RGB'),(0,0));ImageDraw.Draw(im).text((12,547),caption,font=font,fill='white');proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
origin=re.search(r'\[([\d.:-]+)\]\[\s*\d+\].*?AKM_AUDIO_START',log);assert origin
trim=max(0,start-stamp(origin.group(1)));dest=out/'AKM_native_candidate.mp4'
subprocess.run([ff,'-v','error','-y','-i',str(silent),'-ss',str(trim),'-i',str(run/'AKMAudio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-t',str(duration),'-movflags','+faststart',str(dest)],check=True)
(out/'manifest.json').write_text(json.dumps({'source_run':str(run),'frames':len(rows),'duration':duration,'audio_trim':trim,'status':'M4 metal + ambientCG redwood finish; animation contact review incomplete' if args.redwood else 'Candidate; original textures missing; contact review incomplete'},indent=2));print(dest)
if args.source_matched:
 (out/'manifest.json').write_text(json.dumps({'source_run':str(run),'frames':len(rows),'duration':duration,'audio_trim':trim,'status':'Source-driven palm and fingers on unchanged M4 arms; Fab Quixel Dirty Metal surface; actual runtime and mixer capture'},indent=2))
if args.equip_only:
 (out/'manifest.json').write_text(json.dumps({'source_run':str(run),'frames':len(rows),'duration':duration,'audio_trim':trim,'status':'Charge-only equip; fixed seated magazine; left idle grip; actual runtime and mixer capture'},indent=2))
if args.soviet:
 (out/'manifest.json').write_text(json.dumps({'source_run':str(run),'frames':len(rows),'duration':duration,'audio_trim':trim,'status':'Soviet Assault Rifle original PBR; retained M4 hands and AKM animation assets; actual runtime and mixer capture'},indent=2))
