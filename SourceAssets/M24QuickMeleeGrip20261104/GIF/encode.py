"""Package the requested saved-pose review GIFs and source-speed videos."""
from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

O=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
families={
    'skeleton_base':'独立默认握把 · 5 发弹匣',
    'skeleton_mag10_balanced':'平衡握把 · 10 发扩容弹匣',
    'skeleton_mag10_phantom':'幻影握把 · 10 发扩容弹匣',
    'skeleton_mag10_stable':'防滑握把 · 10 发扩容弹匣',
}
outputs={}
for family,title in families.items():
    folder=O/family;combined=folder/'combined';combined.mkdir(exist_ok=True)
    frames=[]
    for i in range(28):
        frame=Image.new('RGB',(1280,480),(24,28,33));d=ImageDraw.Draw(frame)
        d.text((14,8),'M24 快速近战 | '+title,fill='white',font=font)
        d.text((14,36),f'第一人称 | 动作时间 {i/30:.3f} s',fill=(196,205,216),font=small)
        d.text((654,36),'外侧观察 | 已保存动作离线预览',fill=(196,205,216),font=small)
        frame.paste(Image.open(folder/f'{i:03d}_fps.png'),(0,60))
        frame.paste(Image.open(folder/f'{i:03d}_arms.png'),(640,60))
        frame.save(combined/f'{i:03d}.png');frames.append(frame)
    samples=Image.new('RGB',(1280,4*240))
    for j,i in enumerate((0,4,7,10,13,17,21,27)):
        samples.paste(frames[i].resize((640,240)),((j%2)*640,(j//2)*240))
    samples.save(O/f'{family}_contact_sheet.jpg',quality=93)
    palette=samples.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    gif_frames=[f.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
    durations=[70 if i%3!=1 else 60 for i in range(28)];durations[0]+=350;durations[-1]+=650
    gif=O/f'{family}_half_speed.gif'
    gif_frames[0].save(gif,save_all=True,append_images=gif_frames[1:],duration=durations,loop=0,optimize=False,disposal=2)
    mp4=O/f'{family}_source_speed.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-framerate','30','-i',str(combined/'%03d.png'),'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True)
    outputs[family]={'title':title,'gif':str(gif),'video':str(mp4),'sheet':str(O/f'{family}_contact_sheet.jpg'),'gif_playback_speed':.5,'video_playback_speed':1.,'gif_idle_holds_seconds':[.35,.65]}
    print('ENCODED',family,flush=True)

grips=Image.new('RGB',(1280,4*450),(24,28,33));d=ImageDraw.Draw(grips)
for j,(family,title) in enumerate(families.items()):
    for col,t in enumerate((.25,.46)):
        x=col*640;y=j*450
        grips.paste(Image.open(O/family/f'contact_{t:.3f}.png'),(x,y+30))
        d.text((x+10,y+5),f'{title} | {t:.3f} s',fill='white',font=small)
grips.save(O/'all_grips_contact_recovery.jpg',quality=94)
(O/'outputs.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
print('M24_MELEE_GIF_ENCODING_COMPLETE',flush=True)
