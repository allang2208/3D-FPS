from pathlib import Path
import subprocess
import cv2, imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
cap=cv2.VideoCapture(str(HERE.parent/'ReferenceV2/kubold-indexed.mp4'))
first=1034;cap.set(cv2.CAP_PROP_POS_FRAMES,first)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
images=[]
for n in range(81):
    ok,ref=cap.read()
    if not ok:raise ValueError('Reference ended early')
    out=Image.new('RGB',(1024,316),'#172331');draw=ImageDraw.Draw(out)
    out.paste(Image.fromarray(cv2.cvtColor(ref,cv2.COLOR_BGR2RGB)).resize((512,288),Image.Resampling.LANCZOS),(0,28))
    path=HERE.parent/'Review/VideoFitV3/StandardIdleEntry/MotionPreview'/f'f{2*n:04}.png'
    out.paste(Image.open(path).convert('RGB').resize((512,288),Image.Resampling.LANCZOS),(512,28))
    draw.text((12,2),f'Kubold 原视频　{(first+n)/60:.3f} s',font=font,fill='white');draw.text((524,2),f'高地阔锋重刃　普通柄　{n/60:.3f} s',font=font,fill='white');images.append(out)
encoder=imageio_ffmpeg.get_ffmpeg_exe();cmd=[encoder,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1024x316','-r','60','-i','-','-an','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(HERE/'HighlandSweep_V3_Comparison.mp4')];subprocess.run(cmd,input=b''.join(im.tobytes() for im in images),check=True)
show=[im.resize((832,256),Image.Resampling.LANCZOS) for im in images[::2]]; delay=[10*(round((i+1)*100/30)-round(i*100/30)) for i in range(len(show))];delay[-1]=400
show[0].save(HERE/'HighlandSweep_V3_Comparison.gif',save_all=True,append_images=show[1:],duration=delay,loop=0,optimize=False)
