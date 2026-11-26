"""Assemble requested native front/side captures and record the scoped review."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR6';V=R/'Review';E=V/'EngineFinal';O=V/'Delivery';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assets=read(E/'assets.json');contact=read(V/'contact_review.json');saved=read(R/'saved_asset.json')
if assets['idle_asset']!=saved['asset']:raise RuntimeError('Unexpected runtime animation')
for target in ('FPSGAMEEditor','FPSGAME'):
 if read(R/'Build'/(target+'-build.json'))['exit_code']!=0:raise RuntimeError('Build incomplete')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
canvas=Image.new('RGB',(880,952),(30,30,30));draw=ImageDraw.Draw(canvas)
for i,(name,label,box) in enumerate([('front','正面：身前轻搭交叠',(260,40,700,940)),('profile_left','侧面：手位收近小腹',(280,40,720,940))]):
 canvas.paste(Image.open(E/(name+'.png')).convert('RGB').crop(box),(i*440,52));draw.text((i*440+14,12),label,font=font,fill='white')
canvas.save(O/'front_and_side.png')
canvas=Image.new('RGB',(1200,652),(30,30,30));draw=ImageDraw.Draw(canvas)
for i,(name,label) in enumerate([('hand_left','双手交叠与手指'),('hand_left_side','前臂、手腕及袖口')]):
 canvas.paste(Image.open(E/(name+'.png')).convert('RGB').resize((600,600),Image.Resampling.LANCZOS),(i*600,52));draw.text((i*600+16,12),label,font=font,fill='white')
canvas.save(O/'hands_and_cuffs.png')
report=dict(status='saved_integrated_and_reviewed',animation=saved['asset'],source_blend=str(R/'Nun_Crossed_Idle_R6.blend'),
 editor_build='success',game_build='success',pose='Original hands overlapping in front, with lowered elbows, reduced forward reach and forearm-aligned palms',
 duration_seconds=12,production_actor_offscreen_capture=assets['production_actor_assembly'],saved_compressed_pose_samples=len(contact['samples']),
 hand_hand_crossings=sum(sum(x['hand_pair_crossings'].values()) for x in contact['samples']),
 exposed_hand_cloth_crossings=sum(v['hand_edge_cloth_crossings']+v['cloth_edge_hand_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 cuff_torso_crossings=sum(v['cuff_edge_torso_crossings']+v['torso_edge_cuff_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 cuff_pair_crossings=sum(v['cuff_other_sleeve_crossings'] for x in contact['samples'] for v in x['sides'].values()),
 interactive_gameplay_tested=False,screenshots=[str(O/'front_and_side.png'),str(O/'hands_and_cuffs.png')])
(R/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('NUN_CROSSED_R6_DELIVERED',report['hand_hand_crossings'],report['exposed_hand_cloth_crossings'])
