from pathlib import Path
import json,gzip,math
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).parent;review=p/'Review'
auth=json.load(gzip.open(p/'authored.json.gz','rt'));comp=json.load(gzip.open(review/'compressed.json.gz','rt'))
native=json.loads((review/'native_cases.json').read_text(encoding='utf-8-sig'));checks=[]
for family in ('base','mag10'):
 peak_p=peak_r=0.
 indices=[i for i,n in enumerate(auth['names']) if not n.startswith('ik_') and (n.endswith('_l') or n.endswith('_r') or n.startswith('WPN_') or n in ('VM_Root','root'))]
 frames=auth['clips'][family]['frames']
 for i,frame in enumerate(frames):
  compressed=comp['clips'][family]['frames'][i*2]
  for j in indices:
   a,b=frame[j],compressed[j];peak_p=max(peak_p,math.dist(a[:3],b[:3])*1000)
   dot=abs(sum(x*y for x,y in zip(a[3:7],b[3:7])))/math.sqrt(sum(x*x for x in a[3:7])*sum(x*x for x in b[3:7]))
   peak_r=max(peak_r,math.degrees(2*math.acos(min(1,dot))))
 protected=[i for i,n in enumerate(auth['names']) if n.endswith('_r') or n.startswith('WPN_') or n in ('VM_Root','root')]
 drift=max(abs(x-y) for f in frames for j in protected for x,y in zip(f[j],frames[0][j]))
 checks.append({'family':family,'visible_bone_compression_position_mm':peak_p,'visible_bone_compression_rotation_degrees':peak_r,'protected_right_hand_weapon_root_channels_drift':drift,'pass':peak_p<.1 and peak_r<.1 and drift==0})
geometry=json.loads((review/'Compressed/geometry.json').read_text());surface=json.loads((review/'Compressed/surface.json').read_text());old=json.loads((review/'Before/anatomy.json').read_text())
report={'native_cases':len(native['cases']),'native_failures':native['failures'],'frames_per_clip':len(geometry),'sample_hz':240,'source_frames_per_clip':289,'duration_seconds':2.4,'magazine_families':checks,
 'old_max_wrist_bend_degrees':max(x['wrist_axis_degrees'] for x in old),'compressed_max_wrist_bend_degrees':max(x['wrist_axis_degrees'] for x in geometry),
 'compressed_elbow_bend_degrees':[min(x['elbow_degrees'] for x in geometry),max(x['elbow_degrees'] for x in geometry)],'compressed_max_bone_length_error_mm':max(x['bone_length_error_mm'] for x in geometry),
 'attachment_surface_key_samples':len(surface),'max_attachment_contact_depth_mm':max(x['attachment_contacts'][k]['inside_solid_depth_mm'] for x in surface for k in ('Base','Leg')),'contact_skin_tolerance_mm':3,
 'source_pose_families_identical':auth['clips']['base']['frames']==auth['clips']['mag10']['frames'],'saved_assets':json.loads((p/'install_receipt.json').read_text())['saved'],
 'normal_editor_started':False,'in_game_acceptance':False,'two_process_multiplayer_test':False,
 'note':'Existing accepted idle hand/fore-end contact is unchanged. Source and compressed contact review used the current V9 skin and corrective morphs. Small skin contact is reported with a 3 mm tolerance, not claimed to be zero intersection.'}
report['scope_passed']=native['failures']==0 and all(c['pass'] for c in checks) and report['max_attachment_contact_depth_mm']<3
(review/'review_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='saved_assets'},ensure_ascii=False))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22);out=Image.new('RGB',(1440,520),(25,28,32));draw=ImageDraw.Draw(out)
for i,(file,label) in enumerate(((review/'Before/0.600_left.png','修正前：手腕随转轴硬转'),(review/'Compressed/0.650_left.png','修正后：已保存的 UE 压缩动作'))):
 im=Image.open(file).convert('RGB');im.thumbnail((720,480));out.paste(im,(i*720,40));draw.text((i*720+18,8),label,font=font,fill=(235,235,235))
out.save(review/'contact-comparison.jpg',quality=93)
if not report['scope_passed']:raise RuntimeError('Review criteria not met')
