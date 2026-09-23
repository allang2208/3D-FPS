"""Expand usable dry floor area; retain physical-sized pipes, tiles, ports and trench."""
import json,copy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROOMS=ROOT.parent/'DungeonRoomShells20260922'
source=ROOT/'Config/rooms-before.json'
if not source.exists():source.write_bytes((ROOMS/'Config/rooms.json').read_bytes())
OLD=json.loads(source.read_text(encoding='utf-8'))

def warp(room,s,p):
    x,y,*z=p
    if room['id']=='Drainage':
        def axis(v,center,half):
            a,b=center-half,center+half;an,bn=center*s-half,center*s+half
            if a<=v<=b:return v+center*(s-1)
            lo,hi=(-4,7) if center==1.5 else (0,14)
            return lo*s+(v-lo)*(an-lo*s)/(a-lo) if v<a else bn+(v-b)*(hi*s-bn)/(hi-b)
        return [axis(x,1.5,1.5),axis(y,7,4)]+z
    if room['id']=='ShoredBreach' and x>=12:return [x+12*(s-1),y+4*(s-1)]+z
    return [x*s,y*s]+z

def enlarge(old,s):
    r=copy.deepcopy(old);f=lambda p:warp(old,s,p)
    r['footprint']=[f(p) for p in old['footprint']] if old['id']=='Drainage' else [[x*s,y*s] for x,y in old['footprint']]
    for key in ('floors','ceilings'):
        r[key]=[]
        for i,(x0,y0,x1,y1,z) in enumerate(old[key]):
            if old['id']=='ShoredBreach' and i==2:
                a=[x0+12*(s-1),y0+4*(s-1)];b=[x1+12*(s-1),y1+4*(s-1)]
            elif old['id']=='Drainage':a=f([x0,y0]);b=f([x1,y1])
            else:a=[x0*s,y0*s];b=[x1*s,y1*s]
            r[key].append(a+b+[z])
    r['columns']=[f(p) for p in old['columns']]
    for key in ('beams','headers'):
        if key in r:r[key]=[[f(a),f(b),*rest] for a,b,*rest in old[key]]
    for op in r['openings']:
        original=next(o for o in old['openings'] if o['id']==op['id']);edge=op['edge']
        a,b=old['footprint'][edge],old['footprint'][(edge+1)%len(old['footprint'])]
        length=math.dist(a,b);p=[a[j]+(b[j]-a[j])*original['center']/length for j in range(2)]
        q=f(p);na=r['footprint'][edge];op['center']=math.dist(na,q)
    for pipe,orig in zip(r['pipes'],old['pipes']):pipe['points']=[f(p) for p in orig['points']]
    for lamp,orig in zip(r['lights'],old['lights']):
        lamp['at']=f(orig['at']);lamp['lumens']=round(orig['lumens']*(1.32 if lamp['at'][0]<12*s else 1));lamp['radius_cm']=round(orig['radius_cm']*s)
    for a,orig in zip(r['anchors'],old['anchors']):a['at']=f(orig['at'])
    if 'trench' in r:
        t=r['trench'];x0,y0,x1,y1=t['rect'];t['rect']=f([x0,y0])+f([x1,y1]);t['bridge_y']=[f([1.5,y])[1] for y in t['bridge_y']]
        t['hazard']['material']='/Game/Dungeons/CombatExpansion20260922/Materials/MI_PusChannelFluid'
        t['hazard']['mesh']='/Game/Dungeons/CombatExpansion20260922/Meshes/SM_PusChannelFluid'
    if 'breach' in r:
        br=r['breach'];center=(br['left']+br['right'])/2*s;width=br['right']-br['left'];br['left']=center-width/2;br['right']=center+width/2
        br['pocket']=[v+(12 if i%2==0 else 4)*(s-1) for i,v in enumerate(br['pocket'])]
    r['combat_expansion_factor']=s
    return r

def clear_area(room):
    """Exact rectangle sweep of floor minus physical walls, column footprints and open trench."""
    floors=[r[:4] for r in room['floors'] if r[4]==0];cuts=[];t=.12
    def edge(a,b,openings=()):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);cursor=0
        intervals=sorted((o['center']-o['width']/2,o['center']+o['width']/2) for o in openings)+[(length,length)]
        for left,right in intervals:
            if left>cursor:
                p=[a[0]+dx*cursor/length,a[1]+dy*cursor/length];q=[a[0]+dx*left/length,a[1]+dy*left/length]
                cuts.append([min(p[0],q[0])-(t if dx==0 else 0),min(p[1],q[1])-(t if dy==0 else 0),max(p[0],q[0])+(t if dx==0 else 0),max(p[1],q[1])+(t if dy==0 else 0)])
            cursor=right
    fp=room['footprint']
    for i,a in enumerate(fp):
        ops=[o for o in room['openings'] if o['edge']==i]
        if room.get('breach',{}).get('edge')==i:
            br=room['breach'];ops=ops+[dict(center=(br['left']+br['right'])/2,width=br['right']-br['left'])]
        edge(a,fp[(i+1)%len(fp)],ops)
    if 'breach' in room:
        x0,y0,x1,y1=room['breach']['pocket']
        for a,b in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1))]:edge(a,b)
    if 'trench' in room:
        tr=room['trench'];x0,y0,x1,y1=tr['rect'];b0,b1=tr['bridge_y'];floors.append([x0,b0,x1,b1])
    cuts.extend([[x-.18,y-.18,x+.18,y+.18] for x,y in room['columns']])
    xs=sorted({v for r in floors+cuts for v in (r[0],r[2])});ys=sorted({v for r in floors+cuts for v in (r[1],r[3])})
    inside=lambda x,y,rs:any(a<x<c and b<y<d for a,b,c,d in rs)
    return sum((b-a)*(d-c) for a,b in zip(xs,xs[1:]) for c,d in zip(ys,ys[1:]) if inside((a+b)/2,(c+d)/2,floors) and not inside((a+b)/2,(c+d)/2,cuts))

def port(r,name):
    op=next(o for o in r['openings'] if o['id']==name);a=r['footprint'][op['edge']];b=r['footprint'][(op['edge']+1)%len(r['footprint'])];length=math.dist(a,b)
    return [r['origin_m'][j]+a[j]+(b[j]-a[j])*op['center']/length for j in range(2)]+[r['origin_m'][2]]

if __name__=='__main__':
    cfg=copy.deepcopy(OLD);report=[]
    for i,old in enumerate(OLD['rooms']):
        before=clear_area(old);lo,hi=1,1.5
        for _ in range(30):
            s=(lo+hi)/2
            if clear_area(enlarge(old,s))<before*1.5:lo=s
            else:hi=s
        r=enlarge(old,hi);cfg['rooms'][i]=r
        report.append(dict(room=r['id'],old_clear_m2=before,new_clear_m2=clear_area(r),factor=hi))
    d,dr,sb=cfg['rooms'];link=cfg['links'][0];link['origin_m']=port(d,'exit');entry=port(dr,'entry');offset=[entry[j]-dr['origin_m'][j] for j in range(2)];dr['origin_m']=[link['origin_m'][0]-offset[0],link['origin_m'][1]+link['length']-offset[1],.94]
    link=cfg['links'][1];link['origin_m']=port(dr,'exit');sb['origin_m']=[link['origin_m'][0]+link['length'],link['origin_m'][1],.94]
    cfg['version']=2;cfg['clear_area_definition']='Floor union minus wall footprints, columns and unbridged trench. Fixed movable props are relocated without scaling.'
    (ROOT/'Config/rooms.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOMS/'Config/rooms.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'Config/area-budget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
