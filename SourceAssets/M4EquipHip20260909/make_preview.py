from pathlib import Path
from bisect import bisect_right
import importlib.util, json, subprocess, csv
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
project=root.parents[1]
run=project/'Saved/GunplayUpgrade/m4-equip-hip-final60'
out=root/'Preview';out.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('capture_export',project/'Tools/AssetPipeline/render_gunplay_preview.py')
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
ffmpeg=str(root.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
frames={int(p.stem.split('_')[1]):p for p in (run/'Frames').glob('Frame_*.png')}
indices=sorted(frames)
timeline=[frames[indices[max(0,bisect_right(indices,i)-1)]] for i in range(72)]
capture.encode_mp4(ffmpeg,timeline,out/'装备与切枪_实机.mp4',(1280,720))
subprocess.run([ffmpeg,'-v','error','-y','-i',str(out/'装备与切枪_实机.mp4'),'-t','1.6','-filter_complex_threads','1','-filter_complex','fps=10,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer','-loop','0',str(out/'腰射位置装备.gif')],check=True)
canvas=Image.new('RGB',(1920,410),(18,22,28));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
for n,(title,path) in enumerate([
 ('修改前：装备时移向中央',project/'Saved/GunplayUpgrade/m4-hk416-final-60/00_Equip.png'),
 ('修改后：在腰射位置装备',timeline[3]),
 ('结束后：直接衔接腰射待机',timeline[15])]):
    canvas.paste(capture.load_rgb(path,(640,360)),(n*640,0));draw.text((n*640+12,370),title,font=font,fill=(242,245,249))
canvas.save(out/'装备位置前后对比.png')
rows=list(csv.reader((run/'equip_samples.csv').open()))
equip=[r for r in rows if int(r[2])==0]
report={'run':str(run),'frames':len(frames),'capture_hz':10,'duration':7.2,
        'equip_samples_from_csv':len(equip),'max_framing_alpha':max(float(r[3]) for r in equip),
        'max_ads_alpha':max(float(r[4]) for r in equip),'max_xy_hip_error_cm':max((float(r[5])**2+(float(r[6])-7)**2)**.5 for r in equip),
        'missing_frames_held':[i for i in range(72) if i not in frames],
        'note':'Actual game frames. 10 Hz capture is not measured gameplay FPS. Original equip clip and duration retained.'}
(out/'preview.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
