"""Pair rendered UE frames at the same source time. Include both wrist views."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

here=Path(__file__).resolve().parent
root=here.parent/'Wrist34'
before=root/'cover_lift_before'
after=root/'cover_lift_verified'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)

def images(folder):
    return [(row['source'],folder/row['file']) for row in json.loads((folder/'review.json').read_text())['frames']]

def cell(seq,time):
    at,path=min(seq,key=lambda entry:abs(entry[0]-time))
    return at,Image.open(path).convert('RGB')

def sheet(label,view):
    canvas=Image.new('RGB',(1280,4*207),'#202327');d=ImageDraw.Draw(canvas)
    for i,(reload,version,run) in enumerate([('normal','修改前',before),('normal','修改后',after),('empty','修改前',before),('empty','修改后',after)]):
        seq=images(run/('lmg_stability_foregrip_'+reload+'_'+view))
        for j,t in enumerate([.53,.69,.84,1.04]):
            at,im=cell(seq,t);canvas.paste(im.resize((316,178)),(j*320,i*207+26))
            d.text((j*320+4,i*207+2),version+' · '+('普通' if reload=='normal' else '空仓')+f'   {at:.2f} s',font=font)
    canvas.save(here/label,quality=94)

def movie(sequences, filename):
    import imageio_ffmpeg
    import subprocess
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x396','-r','30','-i','-','-an','-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(here/filename)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for reload in ['normal','empty']:
        frames=sequences[reload]
        for t in np.linspace(.30,1.30,73):
            tile=Image.new('RGB',(1280,396),'#202327');d=ImageDraw.Draw(tile)
            for j,(seq,caption) in enumerate(zip(frames,['修改前','修改后'])):
                at,im=cell(seq,t);tile.paste(im.resize((640,360)),(j*640,36))
                d.text((j*640+6,5),caption+' · '+('普通换弹' if reload=='normal' else '空仓换弹')+f'   {at:.2f} s',font=font)
            proc.stdin.write(tile.tobytes())
    proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('Video encoding failed')

def variants():
    grips=[('false','无前握把'),('lmg_stability_foregrip','机枪稳固'),('vertical','垂直'),('tactical_vertical','战术垂直'),('angled','斜角'),('canted','侧倾'),('prism','棱镜')]
    for mode in ('normal','empty'):
        out=Image.new('RGB',(1280,7*182),'#202327');d=ImageDraw.Draw(out)
        for row,(key,title) in enumerate(grips):
            seq=images(after/(key+'_'+mode+'_player'))
            for col,t in enumerate((.55,.69,.85,1.12)):
                at,im=cell(seq,t);out.paste(im.resize((282,158)),(col*320,row*182+24))
                d.text((col*320+3,row*182),title+f'   {at:.2f} s',font=font)
        out.save(here/(mode+'-grips.jpg'),quality=92)

def compare_owner(run):
    old=here.parents[1]/'LMGStabilityGrip20261111/Review02/WireRuns/20261111-194119'
    sheet=Image.new('RGB',(1320,4*218),'#202327');draw=ImageDraw.Draw(sheet)
    sequences={'normal':[],'empty':[]}
    for row,(case,folder,title) in enumerate([(0,old,'修改前'),(0,run,'修改后'),(1,old,'修改前'),(1,run,'修改后')]):
        seq=[]
        visual=folder/'host/Visual'
        for line in (visual/'owner.jsonl').read_text(encoding='utf-8-sig').splitlines():
            r=json.loads(line)
            if r['case']==case and r['stage']==3 and r['reloading'] and (visual/'Owner'/r['image']).is_file():
                seq.append((r['source_time'],visual/'Owner'/r['image']))
        sequences['empty' if case else 'normal'].append(seq)
        milestones=(.50,.62,.78,.94) if case else (.44,.61,.73,.85)
        for col,t in enumerate(milestones):
            at,im=cell(seq,t);sheet.paste(im.resize((326,183)),(col*330,row*218+30))
            draw.text((col*330+4,row*218+4),title+' · '+('空仓' if case else '普通')+f'  {at:.2f} s',font=font)
    sheet.save(here/'player-viewport.jpg',quality=95)
    movie(sequences,'player-lid-lift.mp4')

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:compare_owner(Path(sys.argv[1]))
    else:
        sheet('cover-player.jpg','player');sheet('cover-wrist.jpg','wrist_palm')
        sheet('cover-wrist-outside.jpg','wrist_left');variants()
        movie({mode:[images(run/('lmg_stability_foregrip_'+mode+'_player')) for run in (before,after)]
               for mode in ('normal','empty')},'lid-lift.mp4')
