"""User-requested reference analysis only; does not author or import animations."""
import json,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
P=Path(__file__).parent
URL='https://www.bilibili.com/video/BV1zz4y117f6/'
HEADERS={'User-Agent':'Mozilla/5.0','Referer':URL}
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=30))
meta=get('https://api.bilibili.com/x/web-interface/view?bvid=BV1zz4y117f6')['data']
page=meta['pages'][0]
play=get(f'https://api.bilibili.com/x/player/playurl?bvid=BV1zz4y117f6&cid={page["cid"]}&qn=80&fnval=16&fourk=0')['data']
video=max((v for v in play['dash']['video'] if v['codecs'].startswith('avc1')),key=lambda v:(v['height'],v['bandwidth']))
local=P/'p1_reference_video_only.mp4'
if not local.exists():
    request=urllib.request.Request(video.get('baseUrl') or video['base_url'],headers=HEADERS)
    with urllib.request.urlopen(request,timeout=40) as response, local.open('wb') as output:
        while chunk:=response.read(1024*1024):output.write(chunk)
overview=P/'Overview';overview.mkdir(exist_ok=True)
with (P/'overview_extraction.log').open('w',encoding='utf-8') as log:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-i',str(local),'-vf','fps=1/8',
                    '-q:v','2',str(overview/'frame_%03d.jpg')],stdout=log,stderr=subprocess.STDOUT,check=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
files=sorted(overview.glob('frame_*.jpg'))
for start in range(0,len(files),9):
    sheet=Image.new('RGB',(1920,1164),'#171a20')
    for j,path in enumerate(files[start:start+9]):
        frame=Image.open(path).convert('RGB');frame.thumbnail((640,360))
        x,y=(j%3)*640,(j//3)*388
        sheet.paste(frame,(x,y));ImageDraw.Draw(sheet).text((x+10,y+360),f'P1 ~{(start+j)*8+4:03d} s',font=font,fill='white')
    sheet.save(overview/f'sheet_{start//9+1:02d}.jpg',quality=94)
(P/'source.json').write_text(json.dumps({'url':URL,'title':meta['title'],'pages':meta['pages'],
    'studied_page':page,'width':video['width'],'height':video['height'],'fps':video['frameRate'],
    'method':'Native public video for analysis; overview sampling is approximate, detailed key frames use timestamps',
    'use':'Local reference study only; no source media redistributed or imported into game assets'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'page':page,'width':video['width'],'height':video['height'],'fps':video['frameRate'],'overview_frames':len(files)},ensure_ascii=False),flush=True)
