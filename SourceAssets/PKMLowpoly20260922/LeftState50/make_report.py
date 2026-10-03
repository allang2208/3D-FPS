"""Create compact visual evidence and summarize this scoped, read-only review."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];OUT=HERE/'Review'
rows=json.loads((OUT/'all_manifest.json').read_text());font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
for group,selected in [('holding',rows[:20]),('reload',rows[20:39]),('framing',rows[39:])]:
    cellh=220 if group=='framing' else 290
    image=Image.new('RGB',(1280,((len(selected)+3)//4)*cellh),(24,27,32));draw=ImageDraw.Draw(image)
    for i,row in enumerate(selected):
        x=i%4*320;y=i//4*cellh;picture=Image.open(row['file']).convert('RGB');picture.thumbnail((320,cellh-30))
        image.paste(picture,(x+(320-picture.width)//2,y+30))
        text=f"{row['family']} {row['action']} {row['time']:.3f}s"
        draw.text((x+5,y+6),text,font=font,fill=(235,235,230))
    image.save(OUT/(group+'_sheet.jpg'),quality=87)
pose=json.loads((HERE/'pose_audit.json').read_text());seams=json.loads((HERE/'seam_blend_audit.json').read_text())
body=json.loads((HERE/'body_seam_audit.json').read_text());manifest=json.loads((HERE/'Input/manifest.json').read_text())
unchanged=[]
for entry in manifest:
    path=PROJECT/'Content'/(entry['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    unchanged.append(hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'])
for filename in ['Weapon','Bare','Brown','Black','Sleeve','Grip_angled','Grip_canted','Grip_vertical','Grip_prism']:
    entry=json.loads((HERE/'Input'/(filename+'.json')).read_text());path=PROJECT/'Content'/(entry['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    unchanged.append(hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'])
summary={'scope':'PKM base and four grip families: idle, aim, fire, aim_fire, reload, reload_empty',
    'clips':len(manifest),'native_samples':sum(e['keys'] for e in manifest),'blend_samples':sum(e['samples'] for e in seams['transitions'].values()),
    'visual_frames':len(rows),'source_assets_unchanged_during_review':all(unchanged),'new_asset_changes':0,
    'pose_flags':pose['flags'],'max_wrist_cuff_gap_mm':max(v['compressed_max_gap_cm'] for v in seams['seams'].values())*10,
    'max_finger_grip_drift_mm':max(v['max_finger_position_change_in_gun_cm'] for v in seams['fingers'].values())*10,
    'max_action_endpoint_position_error_mm':max(v['cm'] for f in pose['transitions'].values() for t in f.values() for v in t.values())*10,
    'max_compression_position_error_mm':max(v['compressed_max_position_error_cm'] for v in pose['clips'].values())*10,
    'body_seams':body,'runtime_playtest':False,'visual_method':'Read-back UE geometry, native split normals, and compressed poses rendered with neutral materials in Blender. No diagnostic cast shadows. 16:9 framing uses authored static hip/action anchors; live camera/recoil layers are not reproduced.'}
(HERE/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
