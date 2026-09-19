from pathlib import Path
from PIL import Image,ImageDraw
import imageio_ffmpeg,subprocess,json,hashlib
R=Path(__file__).resolve().parent;out=R/'delivery'
files=sorted((R/'preview_frames').glob('*.png'));assert len(files)==36
frames=[Image.open(p).convert('RGB') for p in files]
frames[0].save(out/'Attack_Howl.gif',save_all=True,append_images=frames[1:],duration=[80,80,90]*12,loop=0,optimize=False)
writer=imageio_ffmpeg.write_frames(str(out/'Howl_silent.mp4'),size=frames[0].size,fps=12,codec='libx264',pix_fmt_in='rgb24',output_params=['-crf','18']);writer.send(None)
for f in frames:writer.send(f.tobytes())
writer.close()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-i',str(out/'Howl_silent.mp4'),'-i','Y:/开发/游戏/素材库/怪物/手脑/声音/howling.mp3','-map','0:v:0','-map','1:a:0','-c:v','copy','-af','apad','-t','3','-c:a','aac','-b:a','192k',str(out/'Attack_Howl.mp4')],check=True)
sheet=Image.new('RGB',(960,680),'#dddddd');draw=ImageDraw.Draw(sheet)
for j,k in enumerate([0,5,10,17,26,35]):
 x=j%3*320;y=j//3*340;sheet.paste(frames[k].resize((320,320)),(x,y));draw.text((x+8,y+323),f'Howl {k/12:.2f}s',fill='black')
sheet.save(out/'Howl_contact_sheet.png')
manifest={'preview_seconds':3,'source_audio_pitch_changed':False,'files':{}}
for name in ['HandBrain_SingleFace.blend','HandBrain_SingleFace.glb','SK_HandBrain_SingleFace.fbx','Attack_Howl.mp4']:
 p=out/name
 with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 manifest['files'][name]={'bytes':p.stat().st_size,'sha256':sha}
(out/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2))
print('SINGLE_FACE_PREVIEW_PACKAGED')
