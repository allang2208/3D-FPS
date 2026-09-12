"""Fetch CMU human capture candidates and the conversion provenance."""
import urllib.request,json,hashlib,concurrent.futures
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Reference/CMU');O.mkdir(parents=True,exist_ok=True)
B='https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/'
paths=['READMEFIRST.txt','cmu-mocap-index-text.txt','data/079/79_01.bvh','data/079/79_04.bvh','data/080/80_71.bvh','data/002/02_07.bvh','data/002/02_08.bvh','data/002/02_09.bvh']
def fetch(p):
    f=O/p.split('/')[-1]
    if not f.exists():
        req=urllib.request.Request(B+p,headers={'User-Agent':'FPSGAME asset review'});f.write_bytes(urllib.request.urlopen(req,timeout=40).read())
    return {'file':f.name,'url':B+p,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,paths))
(O/'sources.json').write_text(json.dumps({'source':'CMU Graphics Lab optical human motion capture; Bruce Hahne BVH conversion','repository':'https://github.com/una-dinosauria/cmu-mocap','official_clip_index':'https://mocap.cs.cmu.edu/search.php?subjectnumber=2','selected_clip':'02_07.bvh','source_fps':120,'files':rows},indent=2));print(json.dumps(rows))
