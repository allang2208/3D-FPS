from pathlib import Path
import requests,json,cv2
from PIL import Image,ImageDraw
O=Path(__file__).parent
headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.bilibili.com/'}
s=requests.Session();s.headers.update(headers)
view=s.get('https://api.bilibili.com/x/web-interface/view',params={'bvid':'BV1Re411e77Q'},timeout=30).json()['data']
play=s.get('https://api.bilibili.com/x/player/playurl',params={'bvid':'BV1Re411e77Q','cid':view['cid'],'qn':64,'fnval':16},timeout=30).json()['data']
v=max((v for v in play['dash']['video'] if v['codecs'].startswith('avc')),key=lambda v:v['height'])
file=O/'reference_video.m4s'
if not file.exists():
    r=s.get(v.get('baseUrl',v.get('base_url')),stream=True,timeout=60);r.raise_for_status()
    with file.open('wb') as f:
        for chunk in r.iter_content(1024*1024):f.write(chunk)
cap=cv2.VideoCapture(str(file));fps=cap.get(cv2.CAP_PROP_FPS)
metadata={'source':'https://www.bilibili.com/video/BV1Re411e77Q/','title':view['title'],'cid':view['cid'],'duration':view['duration'],'fps':fps,'width':v['width'],'height':v['height'],'requested_seconds':[40,52],'use':'Local reference study only; not redistributed as game content'}
(O/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
cols=4;tw=426;th=266;times=list(range(40,53));sheet=Image.new('RGB',(cols*tw,((len(times)+cols-1)//cols)*th),(26,26,26));draw=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read()
    if not ok:raise RuntimeError(t)
    im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.save(O/f'{t:05.1f}.jpg',quality=94)
    im.thumbnail((tw,240));x=(i%cols)*tw;y=(i//cols)*th;sheet.paste(im,(x,y+24));draw.text((x+8,y+5),f'{t:.2f} s',fill='white')
sheet.save(O/'40-52_sheet.jpg',quality=94)
cap.release()
print(json.dumps({'downloaded_bytes':file.stat().st_size,'fps':fps,'frames':len(times)}))
