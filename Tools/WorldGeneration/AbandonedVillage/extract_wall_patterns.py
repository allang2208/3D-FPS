"""Preserve the demo's native overlapping wall fragments as small assemblies."""
import json
import math
import copy
from pathlib import Path
from layout_geometry import rotate
from wall_support import fit_instance

folder=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsVillage/DemoRevision20261114'
demo=json.loads((folder/'demo-walls.json').read_text())
walls=copy.deepcopy(demo['maps']['SL_Demonstration_StaticMeshes']['walls'])
# Demo pieces can be flipped and may depend on its sloping terrain. Keep its XY
# assemblies, but fit each piece to this village's flat pad using real stone geometry.
for wall in walls:
    fit_instance(wall)
meshes=demo['meshes']
parents=list(range(len(walls)))
def root(i):
    while parents[i]!=i:
        parents[i]=parents[parents[i]];i=parents[i]
    return i
def angle(a,b): return abs((a-b+90)%180-90)
def center(w):
    lo,hi=meshes[w['mesh']]['bounds']
    dx,dy=rotate((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,w['rot'][1])
    return (w['pos'][0]+dx,w['pos'][1]+dy)
for i,a in enumerate(walls):
    ca=center(a);ba=meshes[a['mesh']]['bounds']
    for j in range(i):
        b=walls[j];bb=meshes[b['mesh']]['bounds'];cb=center(b)
        if angle(a['rot'][1],b['rot'][1])>13:continue
        x,y=rotate(cb[0]-ca[0],cb[1]-ca[1],-a['rot'][1])
        if abs(y)<65 and abs(x)<(ba[1][0]-ba[0][0]+bb[1][0]-bb[0][0])*.5+75:
            parents[root(i)]=root(j)
groups={}
for i in range(len(walls)):groups.setdefault(root(i),[]).append(i)

def pattern(ids):
    yaw=walls[ids[0]]['rot'][1]
    if yaw>90:yaw-=180
    if yaw<-90:yaw+=180
    projected=[]
    for i in ids:
        w=walls[i];lo,hi=meshes[w['mesh']]['bounds']
        for x in (lo[0],hi[0]):
            for y in (lo[1],hi[1]):
                dx,dy=rotate(x,y,w['rot'][1])
                projected.append(rotate(w['pos'][0]+dx,w['pos'][1]+dy,-yaw))
    xmin,xmax=min(p[0] for p in projected),max(p[0] for p in projected)
    ymin,ymax=min(p[1] for p in projected),max(p[1] for p in projected)
    pivot=((xmin+xmax)*.5,(ymin+ymax)*.5,0.)
    parts=[]
    for i in ids:
        w=walls[i];x,y=rotate(w['pos'][0],w['pos'][1],-yaw)
        parts.append(dict(mesh=w['mesh'],pos=[x-pivot[0],y-pivot[1],w['pos'][2]-pivot[2]],
                          rot=[w['rot'][0],w['rot'][1]-yaw,w['rot'][2]],materials=w['materials'],source_index=i))
    return dict(parts=parts,length_cm=xmax-xmin,width_cm=ymax-ymin,source_indices=ids)

patterns=[]
for ids in groups.values():
    yaw=walls[ids[0]]['rot'][1]
    ids.sort(key=lambda i:rotate(*center(walls[i]),-yaw)[0])
    for start in range(0,len(ids),3):
        chunk=ids[start:start+4]
        item=pattern(chunk)
        if item['width_cm']<145 and item['length_cm']<1050:
            patterns.append(item)
# Single original fragments are only used for short residual ends and real breaks.
for name in meshes:
    if 'Piece' not in name:continue
    index=next(i for i,w in enumerate(walls) if w['mesh']==name)
    patterns.append(pattern([index]))
data=dict(source='/Game/UnrealNormandy/Levels/SL_Demonstration_StaticMeshes',source_count=len(walls),
          meshes=meshes,patterns=patterns)
(folder/'wall-patterns.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('DEMO_NATIVE_PATTERNS',len(patterns),'source_groups',len(groups))
for i,p in enumerate(patterns):
    print(i,round(p['length_cm']),round(p['width_cm']),[x['mesh'].split('Piece')[-1] for x in p['parts']])
