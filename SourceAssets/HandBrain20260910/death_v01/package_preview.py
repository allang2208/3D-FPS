from pathlib import Path
from PIL import Image,ImageDraw
import imageio_ffmpeg,json,struct,hashlib
R=Path(__file__).resolve().parent;out=R/'delivery'
with (out/'HandBrain_FiveActions.glb').open('rb') as f:
 f.read(12);size,kind=struct.unpack('<II',f.read(8));doc=json.loads(f.read(size))
clips={}
for a in doc['animations']:
 ts=[doc['accessors'][x['input']] for x in a['samplers']]
 clips[a['name']]=max(t['max'][0] for t in ts)-min(t['min'][0] for t in ts)
assert set(clips)=={'Idle','Move','Attack_Slam','Attack_Howl','Death'} and abs(clips['Death']-2.8)<1e-5
(out/'glb_validation.json').write_text(json.dumps(clips,indent=2))
frames=[Image.open(p).convert('RGB') for p in sorted((R/'preview_frames').glob('*.png'))];assert len(frames)==42
frames[0].save(out/'Death.gif',save_all=True,append_images=frames[1:],duration=[70,70,60]*14,loop=0,optimize=False)
w=imageio_ffmpeg.write_frames(str(out/'Death.mp4'),size=frames[0].size,fps=15,codec='libx264',pix_fmt_in='rgb24',output_params=['-crf','18']);w.send(None)
for f in frames:w.send(f.tobytes())
w.close()
sheet=Image.new('RGB',(960,680),'#ddd');draw=ImageDraw.Draw(sheet)
for j,i in enumerate([0,6,12,17,25,41]):
 x=j%3*320;y=j//3*340;sheet.paste(frames[i].resize((320,320)),(x,y));draw.text((x+8,y+323),f'Death {i/15:.2f}s',fill='black')
sheet.save(out/'Death_contact_sheet.png')
manifest={}
for name in ['HandBrain_FiveActions.blend','SK_HandBrain_FiveActions.fbx','HandBrain_FiveActions.glb','Death.mp4']:
 p=out/name
 with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 manifest[name]={'bytes':p.stat().st_size,'sha256':digest}
(out/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2))
print('DEATH_PREVIEW_PACKAGED')
