"""Compose unretouched renders and actual UE capture sequences for review."""
import datetime as dt,hashlib,json,re,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent));from case import *
P=O.parents[1];D=O/'Delivery';D.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
TITLES={'canted':'45°侧倾握把','prism':'棱镜阻手器'}
def board(name,cells,cols=2,width=650):
 height=500;im=Image.new('RGB',(cols*width,((len(cells)+cols-1)//cols)*height),'#10171d');draw=ImageDraw.Draw(im)
 for i,(label,path) in enumerate(cells):
  x,y=i%cols*width,i//cols*height;draw.text((x+12,y+10),label,font=font,fill='#e7f2f5');pic=Image.open(path).convert('RGB');pic.thumbnail((width,height-48));im.paste(pic,(x+(width-pic.width)//2,y+48+(height-48-pic.height)//2))
 im.save(D/name)
def shot(w,v,n):return P/f'Saved/ForegripAudit/vre-extended-{w}-{v}/{n}.png'
board('Source_Before_After.png',[(f'M4 {TITLES[v]} · {label}',O/f'Static/m4/{v}/{which}_palm.png') for v in ['canted','prism'] for which,label in [('before','修改前'),('after','VRE 抓握')]])
if '--source-only' in sys.argv:raise SystemExit(0)
board('Runtime_Grips.png',[(f'{w.upper()} · {TITLES[v]}',shot(w,v,'grasp_closeup')) for w,v in FAMILIES])
board('Player_Views.png',[(f'{w.upper()} · {TITLES[v]} · 玩家视点',shot(w,v,'player_grasp_review')) for w,v in FAMILIES])
board('Wrist_Views.png',[(f'{w.upper()} · {TITLES[v]} · 腕肘',shot(w,v,'wrist_review')) for w,v in FAMILIES])
runtime={}
for w,v in FAMILIES:
 run=f'vre-extended-{w}-{v}';log=(O/f'runtime-{run}.log').read_text(errors='replace');assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
 loaded=re.search(r'FOREGRIP_AUDIT_LOADED idle=(\S+)',log).group(1);assert ('M4VREGripExtensions' if w=='m4' else 'GripVREExtensions') in loaded
 runtime[w+':'+v]={'run':run,'checks':len(re.findall('FOREGRIP_AUDIT: PASS',log)),'failures':0,'loaded_idle':loaded,'exit_code':0}
 stamps={name:dt.datetime.strptime(stamp,'%Y.%m.%d-%H.%M.%S:%f').timestamp() for stamp,name in re.findall(r'\[([\d.\-:]+)\]\[\s*\d+\].*Tracing Screenshot "([^"]+)"',log)}
 frames=[(shot(w,v,n),1.1) for n in ['idle','player_grasp_review','grasp_closeup','wrist_review','ads']];review=[]
 for clip,returned in [('standard_normal',6),('standard_empty',8),('drum_normal',10),('drum_empty',12)]:
  paths=sorted(p for p in shot(w,v,'idle').parent.glob(clip+'_*.png') if p.stem in stamps);assert paths
  for i,p in enumerate(paths):
   duration=stamps[paths[i+1].stem]-stamps[p.stem] if i+1<len(paths) else .12;assert 0<duration<2;frames.append((p,duration))
  frames.append((shot(w,v,f'returned_{returned}'),.6))
  for i in [0,int((len(paths)-1)*.15),int((len(paths)-1)*.7),len(paths)-1]:review.append((f'{w.upper()} {clip} · {i}',paths[i]))
 board(f'{w}_{v}_ReloadReview.jpg',review,4,440)
 concat=D/f'{w}_{v}.ffconcat';concat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {duration:.6f}\n" for p,duration in frames)+f"file '{frames[-1][0].as_posix()}'\n")
 ff=P/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
 subprocess.run([str(ff),'-v','error','-y','-safe','0','-i',str(concat),'-r','30','-c:v','libx264','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(D/f'{w}_{v}.mp4')],check=True)
assets=read(OUT/'asset_validation.json');source=read(OUT/'source_validation.json');assert len(assets)==len(source)==36 and all(x['passed'] for x in assets.values())
geometry={}
for w,v in FAMILIES:
 data=read(OUT/w/v/'geometry.json');geometry[w+':'+v]={'samples':len(data),'grip_intersection_samples':sum(bool(x['crossing_hand_triangles']) for x in data.values()),'finger_self_intersection_samples':sum(bool(x['self']) for x in data.values())}
fits=read(O/'fits.json')
result={'date':'2026-09-12','scope':'M4/AKM canted and prism, nine clips per family','donor':'VRE GrabAnimation reused from MannyGraspDonor20260912','source_contract_passed':36,'ue_asset_readback_passed':36,'native_build':'9122820 Succeeded','runtime':runtime,'geometry':geometry,'geometry_scope':'Sampled skinned glove/attachment and finger/finger surfaces. Residual contacts remain. Prism internal overlap explicitly allowed; no zero-intersection claim for canted.','arm':{k:f['arm'] for k,f in fits.items()},'compression_maxima':{k:max(x[k] for x in assets.values()) for k in ['compression_position_cm','compression_rotation_deg','preserved_nonleft_cm','preserved_contact_cm']},'animation_times':'Existing duration, sample rates, right-hand and mechanical motion, reload contact intervals retained. Quaternion sign equivalence respected.','preview':'Source renders and actual UE screenshots. Player-eye closeups use FOV30. Silent timestamp-based sequences, not native30fps video or audio validation.','materials':'Current runtime material retained; source Blender files use earlier patterned material.','user_visual_acceptance':'Vertical donor direction approved; these canted/prism variants await user review.'}
(OUT/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
manifest=[{'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.suffix in ['.blend','.fbx']]
assert len(manifest)==76;(OUT/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2));print('EXTENSION_DELIVERY_READY',json.dumps(result,ensure_ascii=False),flush=True)
