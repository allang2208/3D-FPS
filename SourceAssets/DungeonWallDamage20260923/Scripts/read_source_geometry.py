import sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
for p in ('Sources','Authored','Config','Receipts'):(ROOT/p).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT.parent/'DungeonRoomShells20260922/Scripts'))
from corridor_surfaces import CorridorSurfaces
s=CorridorSurfaces(ROOT,{},{});out=[]
for width,records,name,lo in s.panels:
    mats={}
    for points,mat,smooth in records:
        d=mats.setdefault(mat,dict(count=0,min=[1e9]*3,max=[-1e9]*3));d['count']+=1
        for p in points:
            for i in range(3):d['min'][i]=min(d['min'][i],p[i]);d['max'][i]=max(d['max'][i],p[i])
    out.append(dict(name=name,width=width,source_start=lo,materials=mats))
(ROOT/'Sources/panels.json').write_text(json.dumps(out,indent=2))
print('WALL_SOURCE_READ',json.dumps(out),flush=True)
