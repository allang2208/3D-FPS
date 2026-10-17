import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).parent;P=O.parents[1];R=P/'Saved/M870PoseAudit/M870PoseAudit_SurfaceFit_R1d_20261016';V=R/'Review'
rows=[json.loads(x) for x in (R/'frames.jsonl').read_text(encoding='utf-8-sig').splitlines()]
def choose(stage,time):return min([x for x in rows if x['wardrobe']=='chainmail' and x['stage']==stage],key=lambda x:abs(x['stage_time']-time))
sheet=Image.new('RGB',(1280,390),(26,28,31));draw=ImageDraw.Draw(sheet)
for i,stage in enumerate(('hip','ads')):
 row=choose(stage,1.4);sheet.paste(Image.open(R/'Frames'/row['image']).resize((640,360)),(i*640,30));draw.text((i*640+12,10),'M870 / CHAINMAIL / '+stage.upper(),fill='white')
sheet.save(V/'chainmail_hip_ads.jpg',quality=92)
for stage in ('reload_normal','reload_empty'):
 sequence=[x for x in rows if x['wardrobe']=='chainmail' and x['stage']==stage]
 images=[]
 for row in sequence:
  im=Image.open(R/'Frames'/row['image']).convert('RGB').resize((640,360));images.append(im.quantize(colors=128))
 images[0].save(V/(stage+'.gif'),save_all=True,append_images=images[1:],duration=67,loop=0,optimize=False)
receipt=json.loads((O/'install_receipt.json').read_text());completion=json.loads((R/'completion.json').read_text());runtime=json.loads((P/'SourceAssets/M870VisualCheck20261016/runtime_receipt.json').read_text(encoding='utf-8-sig'))
report={'saved_animation_count':len(receipt['saved']),'installation_completed':receipt['completed'],'published_grip':'optimized_grip_r1.json','runtime_label':R.name,'runtime_completed':completion['completed'],'runtime_exit_code':runtime['exit_code'],'captured_frames':len(rows),'frame_png_count':len(list((R/'Frames').glob('*.png'))),'scope':['bare and chainmail hip','ADS and return after reload','normal reload from 3 to 7','empty reload from 0 to 7 including final pump'],'visual_review':'Hip/ADS and selected reload contact/transition frames inspected; the preceding gross left-arm twist and sight occlusion were not reproduced. This is not a claim of zero subpixel intersections in every pose.','audio_tested':False,'multiplayer_tested':False,'review_directory':str(V),'unchanged':['gun and native bind','skin weights and shared outfit assets','right hand and weapon tracks','reload events and weapon stats'],'files':[]}
for path in sorted((P/'Content/Weapons/M870/Tactical20261015/Animations').glob('*.uasset')):report['files'].append({'path':str(path.relative_to(P)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(O/'delivery.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k not in ('files','unchanged')})
