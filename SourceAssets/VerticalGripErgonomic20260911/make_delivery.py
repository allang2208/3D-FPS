from pathlib import Path
import json,hashlib,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;ROOT=O.parents[1]
summary={'revision':'ergonomic-photo-reference','members':{},'native_build':'UnrealEditor-FPSGAME-2026096187.dll','packaged_build_verified':False,'audio_changed':False,'manual_control_rig_preserved':'/Game/Weapons/M4ArmsIKEditor/LS_M4_Vertical_Idle_IK_Edit','pose_metrics':json.loads((O/'final_pose_metrics.json').read_text()),'saved_assets':json.loads((O/'saved_asset_validation.json').read_text())}
assert 'Result: Succeeded' in (O/'native_build.log').read_text(encoding='utf-8-sig')
for variant,title,run in [('vertical','Vertical','vertical-ergonomic-v1'),('prism','Prism','prism-ergonomic-v1')]:
 d=O/variant;frames=ROOT/'Saved/ForegripAudit'/run;log=(d/f'runtime-{run}.log').read_text(encoding='utf-8-sig');assert 'FOREGRIP_AUDIT: COMPLETE failures=0' in log and 'FOREGRIP_AUDIT: FAIL' not in log
 g=json.loads((d/'geometry_contact_full.json').read_text());assert len(g)==446 and all(r['crossing_hand_triangles']==0 for r in g.values())
 for name in ['idle.png','ads.png','grasp_closeup.png','grasp_front.png','wrist_review.png','returned_8.png','returned_12.png']:shutil.copy2(frames/name,d/name)
 entries=[]
 for branch,returned in [('standard_normal','returned_6.png'),('standard_empty','returned_8.png'),('drum_normal','returned_10.png'),('drum_empty','returned_12.png')]:
  shots=sorted(frames.glob(branch+'_*.png'));assert shots;entries.append((frames/'idle.png',.6))
  for i,p in enumerate(shots):entries.append((p,max(.016,min(.25,shots[i+1].stat().st_mtime-p.stat().st_mtime)) if i+1<len(shots) else .06))
  entries.append((frames/returned,.8))
 concat=d/'gameplay.ffconcat';concat.write_text('ffconcat version 1.0\n'+''.join(f"file '{p.as_posix()}'\nduration {t}\n" for p,t in entries)+f"file '{entries[-1][0].as_posix()}'\n")
 ff=ROOT/'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe';video=d/f'M4_{title}_Ergonomic_Gameplay.mp4';subprocess.run([str(ff),'-y','-v','error','-safe','0','-f','concat','-i',str(concat),'-r','30','-c:v','libx264','-crf','19','-pix_fmt','yuv420p',str(video)],check=True)
 summary['members'][variant]={'runtime_passes':log.count('FOREGRIP_AUDIT: PASS '),'runtime_failures':0,'surface_samples':len(g),'hand_grip_crossings':0,'import_report':json.loads((d/'import_report.json').read_text()),'animation_build':json.loads((d/'animation_build.json').read_text()),'fbx_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.glob('*.fbx')},'preview':str(video),'preview_note':'Actual game screenshot sequence; silent visual evidence.'}
summary['total_runtime_passes']=sum(v['runtime_passes'] for v in summary['members'].values());summary['source_self_contact_comparison']=json.loads((O/'preserved_source_self_contacts.json').read_text());(O/'acceptance.json').write_text(json.dumps(summary,indent=2))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',34)
for kind in ['arm','palm']:
 a=Image.open(O/f'before_vertical_{kind}.png').convert('RGB');b=Image.open(O/f'final_vertical_{kind}.png').convert('RGB');canvas=Image.new('RGB',(2000,820),(25,29,34));draw=ImageDraw.Draw(canvas);draw.text((35,18),'调整前',font=font,fill='white');draw.text((1035,18),'本次调整',font=font,fill='white');canvas.paste(a,(0,70));canvas.paste(b,(1000,70));canvas.save(O/f'compare_{kind}.jpg',quality=95)
print('ERGONOMIC_ACCEPTANCE',summary['total_runtime_passes'],'runtime passes, 892 surface samples')
