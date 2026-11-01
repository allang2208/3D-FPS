import json,subprocess,sys
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'PythonDeps'))
import imageio_ffmpeg
j=json.loads((O/'reference-play.json').read_text());url=j['data']['durl'][0]['url'];ff=imageio_ffmpeg.get_ffmpeg_exe()
out=O/'Reference';out.mkdir(exist_ok=True)
args=[ff,'-hide_banner','-loglevel','error','-y','-user_agent','Mozilla/5.0','-headers','Referer: https://www.bilibili.com/\r\n','-ss','64.5','-i',url,'-t','3','-an','-vf','fps=8,scale=960:-2',str(out/'ref_%03d.png')]
r=subprocess.run(args,capture_output=True,text=True,timeout=90)
if r.returncode:raise RuntimeError(r.stderr[:1200])
(O/'reference_notes.json').write_text(json.dumps({'url':'https://www.bilibili.com/video/BV1Au9CYNEau/','requested_seconds':[65,67],'extracted_seconds':[64.5,67.5],'frame_rate':8,'source_weapon':'COD20 M200 as named in video title','use':'motion reference only'},indent=2))
print('M24_REFERENCE_FRAMES_SAVED',len(list(out.glob('*.png'))))
