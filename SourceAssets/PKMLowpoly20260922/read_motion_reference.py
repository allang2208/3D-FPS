"""Fetch the user-selected public reference for offline frame-by-frame authoring.
No login cookies, paid quality, or generated asset uploads are used.
"""
import json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).parent/'References'
ROOT.mkdir(exist_ok=True)
BVID='BV1jHeA6sEmj';PAGE='https://www.bilibili.com/video/'+BVID+'/'
HEAD={'User-Agent':'Mozilla/5.0','Referer':PAGE}
def data(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=30))
v=data('https://api.bilibili.com/x/web-interface/view?bvid='+BVID)
if v.get('code')!=0:raise RuntimeError('Reference metadata unavailable: '+str(v.get('code')))
d=v['data'];cid=d['pages'][0]['cid']
play=data(f'https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={cid}&qn=32&fnval=0&fourk=0')
if play.get('code')!=0:raise RuntimeError('Public playback unavailable: '+str(play.get('code')))
streams=play['data'].get('durl')
if not streams:raise RuntimeError('No public progressive reference stream; no authenticated fallback attempted')
dest=ROOT/'PKM_UserReloadReference.mp4'
if not dest.exists():
 with urllib.request.urlopen(urllib.request.Request(streams[0]['url'],headers=HEAD),timeout=45) as src,dest.open('wb') as dst:
  while chunk:=src.read(1048576):dst.write(chunk)
rec={'source':PAGE,'title':d['title'],'cid':cid,'duration':d['duration'],'public_quality':play['data'].get('quality'),'local_file':dest.name,'purpose':'Private animation reference only; not redistributed or copied as animation data'}
(ROOT/'motion_reference.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(dest),'duration':d['duration'],'bytes':dest.stat().st_size},ensure_ascii=True))
