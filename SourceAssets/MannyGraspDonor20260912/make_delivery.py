"""Package unretouched source renders and time-stamped UE screenshots."""
import datetime as dt,hashlib,json,re,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;P=O.parents[1];D=O/'Delivery';D.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
def board(name,cells,cols=2,width=650):
 height=500;im=Image.new('RGB',(cols*width,((len(cells)+cols-1)//cols)*height),'#10171d');draw=ImageDraw.Draw(im)
 for i,(label,path) in enumerate(cells):
  x,y=i%cols*width,i//cols*height;draw.text((x+12,y+10),label,font=font,fill='#e7f2f5')
  pic=Image.open(path).convert('RGB');pic.thumbnail((width,height-48));im.paste(pic,(x+(width-pic.width)//2,y+48+(height-48-pic.height)//2))
 im.save(D/name)
def shot(w,n):return P/f'Saved/ForegripAudit/vre-natural-{w}-vertical/{n}.png'
board('Grip_Comparison.png',[
 ('前一版 M4 · 已拒绝',P/'Saved/ForegripAudit/opposed-m4-vertical/grasp_closeup.png'),
 ('本轮 M4 · 原始手套材质的 Blender 预览',O/'Opening/0.8/aligned_palm.png'),
 ('本轮 M4 · UE 本轮截图中的白手套材质',shot('m4','grasp_closeup')),
 ('本轮 AKM · UE 本轮截图中的白手套材质',shot('akm','grasp_closeup'))])
board('Player_Wrist_Views.png',[(f'{w.upper()} · {label}',shot(w,n)) for n,label in [('player_grasp_review','玩家视点近景'),('wrist_review','腕肘连接')] for w in ['m4','akm']])
board('Original_Donor.png',[('GitHub GrabAnimation · 原始手模',O/'vre_back.png'),('转入当前手套 · 统一闭合幅度 80%',O/'Opening/0.8/aligned_palm.png')])
runtime={}
for w in ['m4','akm']:
 run=f'vre-natural-{w}-vertical';log=(O/f'runtime-{run}.log').read_text(errors='replace')
 assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
 loaded=re.search(r'FOREGRIP_AUDIT_LOADED idle=(\S+)',log).group(1);assert 'VRENatural' in loaded
 runtime[w]={'run':run,'checks':len(re.findall('FOREGRIP_AUDIT: PASS',log)),'failures':0,'loaded_idle':loaded,'exit_code':0}
 stamps={name:dt.datetime.strptime(stamp,'%Y.%m.%d-%H.%M.%S:%f').timestamp() for stamp,name in re.findall(r'\[([\d.\-:]+)\]\[\s*\d+\].*Tracing Screenshot "([^"]+)"',log)}
 frames=[(shot(w,n),1.1) for n in ['idle','player_grasp_review','grasp_closeup','wrist_review','ads']];review=[]
 for clip,returned in [('standard_normal',6),('standard_empty',8),('drum_normal',10),('drum_empty',12)]:
  paths=sorted(p for p in shot(w,'idle').parent.glob(clip+'_*.png') if p.stem in stamps);assert paths
  for i,p in enumerate(paths):
   dur=stamps[paths[i+1].stem]-stamps[p.stem] if i+1<len(paths) else .12
   assert 0<dur<2;frames.append((p,dur))
  frames.append((shot(w,f'returned_{returned}'),.6))
  for i in [0,int((len(paths)-1)*.15),int((len(paths)-1)*.7),len(paths)-1]:review.append((f'{w.upper()} {clip} · {i}',paths[i]))
 board(f'{w}_ReloadReview.jpg',review,4,440)
 concat=D/(w+'.ffconcat');concat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {duration:.6f}\n" for p,duration in frames)+f"file '{frames[-1][0].as_posix()}'\n")
 ff=P/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
 subprocess.run([str(ff),'-v','error','-y','-safe','0','-i',str(concat),'-r','30','-c:v','libx264','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(D/(w+'.mp4'))],check=True)
assets=json.loads((O/'Final/asset_validation.json').read_text());source=json.loads((O/'Final/source_validation.json').read_text())
assert len(assets)==len(source)==18 and all(x['passed'] for x in assets.values())
geometry={}
for w in ['m4','akm']:
 data=json.loads((O/f'Final/{w}/vertical/geometry.json').read_text());geometry[w]={'samples':len(data),'grip_intersection_samples':sum(bool(x['crossing_hand_triangles']) for x in data.values()),'finger_self_intersection_samples':sum(bool(x['self']) for x in data.values())}
result={'date':'2026-09-12','candidate':'VRE GrabAnimation anatomical mirror, closure 0.8, rigid fist alignment','scope':'M4 and AKM vertical grip, nine clips each; canted and handstops unchanged','source_contract_passed':18,'ue_asset_readback_passed':18,'runtime':runtime,'native_build':'9122750 Succeeded; concurrent later builds preserved','geometry':geometry,'geometry_status':'Residual glove/grip and adjacent-finger surface intersections remain; not zero-penetration acceptance. Sampled surfaces only.','compression_maxima':{k:max(x[k] for x in assets.values()) for k in ['compression_position_cm','compression_rotation_deg','preserved_nonleft_cm','preserved_contact_cm']},'materials':'At the original capture time MI_Manny_01/02 parent was ArmsBlackWhiteTrial; this task did not change it. Blender donor previews retain earlier patterned material.','video':'Actual UE screenshot sequence using logged capture intervals, encoded 30 fps; silent, not native 30 fps recording or sound acceptance.','user_visual_acceptance':'2026-09-12: user approved the vertical-grip direction and later confirmed the same-method canted/handstop result successful, requesting workflow standardization. Prior opposed-thumb iteration rejected.'}
(O/'Final/validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
manifest=[]
for p in sorted((O/'Final').rglob('*')):
 if p.suffix in ['.fbx','.blend']:manifest.append({'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(manifest)==38
(O/'Final/delivery_manifest.json').write_text(json.dumps(manifest,indent=2))
print('DONOR_DELIVERY_READY',json.dumps(result,ensure_ascii=False),flush=True)
