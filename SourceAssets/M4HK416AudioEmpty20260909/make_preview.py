"""Mux the original realtime mixer recording with its own game capture frames."""
from pathlib import Path
from bisect import bisect_right
import importlib.util, json, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
RUN=PROJECT/'Saved/GunplayUpgrade/m4-hk416-av60-audible'
OUT=ROOT/'Preview'
OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('capture_export',PROJECT/'Tools/AssetPipeline/render_gunplay_preview.py')
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
ffmpeg=str(ROOT.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
frames={int(p.stem.split('_')[1]):p for p in (RUN/'Frames').glob('Frame_*.png')}
indices=sorted(frames)
timeline=[frames[indices[max(0,bisect_right(indices,i)-1)]] for i in range(142)]
capture.encode_mp4(ffmpeg,timeline,OUT/'game_frames_silent.mp4',(1280,720))
audio=(ROOT/'audio_validation_m4-hk416-av60-audible.json')
proof=json.loads(audio.read_text())
audio_start=2.8-proof['first_audit_elapsed']
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(OUT/'game_frames_silent.mp4'),'-ss',str(audio_start),'-i',str(RUN/'GunplayAudio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','14.2','-movflags','+faststart',str(OUT/'M4_HK416_实际音效与空仓换弹.mp4')],check=True)
canvas=Image.new('RGB',(1280,792),(18,22,28));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
for x,y,index,title in [(0,0,80,'插匣、拍实'),(640,0,86,'左手抬向枪机释放钮'),(0,396,89,'按压释放、枪机回位'),(640,396,99,'收手、恢复持枪')]:
    canvas.paste(capture.load_rgb(timeline[index],(640,360)),(x,y))
    draw.text((x+12,y+363),title,font=font,fill=(240,244,249))
canvas.save(OUT/'空仓动作关键帧.png')
report=dict(source_run=str(RUN),source_frames=len(frames),held_missing_indices=[i for i in range(142) if i not in frames],
            output_frames=142,capture_fps=10,duration=14.2,actual_mixer_audio=str(RUN/'GunplayAudio.wav'),
            audio_trim_start=audio_start,video=str(OUT/'M4_HK416_实际音效与空仓换弹.mp4'),
            note='Same-run actual mixer output. Only timeline-origin trim; no per-event audio shifts or replacement sounds. 10 Hz screenshot capture creates stalls and is not a gameplay FPS benchmark.')
(OUT/'preview.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
