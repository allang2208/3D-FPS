"""Read-only offline model of FPlan. No UE launch/assets/map mutation.

The RNG matches UE 5.8 RandomStream.h. A saved engine graph is used to cross-check
the model before exercising additional seeds. It is not a PIE/physics test.
"""
import json, math, struct, time, collections, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SNAP=ROOT/'Snapshot'; OUT=ROOT/'Results'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
class Rand:
    def __init__(self,seed):self.seed=seed&0xffffffff
    def fraction(self):
        self.seed=(self.seed*196314165+907633515)&0xffffffff
        return (self.seed>>9)/8388608.
    def range(self,a,b):return a+int(f32(self.fraction()*(b-a+1)))
    def shuffle(self,a):
        for i in range(len(a)-1,0,-1):
            j=self.range(0,i);a[i],a[j]=a[j],a[i]
def rot(v,yaw):
    c=math.cos(math.radians(yaw));s=math.sin(math.radians(yaw))
    return (c*v[0]-s*v[1],s*v[0]+c*v[1],v[2])
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def transform(v,t):return add(rot(v,t[1]),t[0])
def box(b,t):
    p=[transform((x,y,z),t) for x in (b['min'][0],b['max'][0]) for y in (b['min'][1],b['max'][1]) for z in (b['min'][2],b['max'][2])]
    return {'min':tuple(min(v[i] for v in p) for i in range(3)),'max':tuple(max(v[i] for v in p) for i in range(3))}
def overlap(a,b,tol=8):return all(min(a['max'][i],b['max'][i])-max(a['min'][i],b['min'][i])>tol for i in (0,1))
class Plan:
    def __init__(self,c):
        self.c=c;self.modules={m['id']:m for m in c['modules']}
        self.combat=c.get('room_ids',['Distribution','Drainage','ShoredBreach'])
        self.reserved={'min':c['reserved_min'],'max':c['reserved_max']}
        self.p=[];self.counts=[];self.budget=0;self.treasure=0;self.rolls=0;self.hits=0
    def fit(self,m,entry,s):
        port=self.modules[m]['ports'][entry]
        yaw=math.degrees(math.atan2(-s[1][1],-s[1][0])-math.atan2(port['normal'][1],port['normal'][0]))
        return sub(s[0],rot(port['position'],yaw)),yaw
    def ports(self,i):
        p=self.p[i];m=self.modules[p['module']]
        return m['ports']+([m['side_sockets'][p['side']]] if p.get('side',-1)>=0 else [])
    def socket(self,i,n):
        port=self.ports(i)[n];p=self.p[i]
        return transform(port['position'],p['t']),rot(port['normal'],p['t'][1]),i
    def place(self,m,t,route,ignore_from=-2,ignore_owner=-2,sector=None):
        module=self.modules[m];b=box(module,t);cells=[box(c,t) for c in module['cells']]
        if ignore_owner!=-1 and any(overlap(c,self.reserved) for c in cells):return False
        for i,p in enumerate(self.p):
            if i==ignore_owner or (ignore_from>=0 and i>=ignore_from):continue
            if overlap(b,p['bounds']) and any(overlap(c,o) for c in cells for o in p['cells']):return False
        if sector:
            origin,direction=sector;side=(-direction[1],direction[0],0)
            for x in (b['min'][0],b['max'][0]):
                for y in (b['min'][1],b['max'][1]):
                    d=sub((x,y,0),origin);f=sum(a*z for a,z in zip(d,direction));s=sum(a*z for a,z in zip(d,side))
                    if f<400 or abs(s)>f*.85+150:return False
        self.p.append(dict(module=m,t=t,route=route,bounds=b,cells=cells,side=-1));return True
    def corridor(self,count,s,route,m='Transit'):
        before=len(self.p);initial=s
        for _ in range(count):
            if not self.place(m,self.fit(m,0,s),route,before,initial[2]):
                del self.p[before:];return None
            s=self.socket(len(self.p)-1,1)
        return s
    def chain(self,n,s,route,sector=None):
        if n==0:return s
        self.budget-=1
        if self.budget<0:return None
        choices=[(m,e) for m in self.combat for e in (0,1)];self.random.shuffle(choices)
        before=len(self.p)
        for m,e in choices:
            for length in (1,2,3,5):
                del self.p[before:]
                end=self.corridor(length,s,route,'Threshold')
                if end is None:continue
                if not self.place(m,self.fit(m,e,end),route,before,-2,sector):continue
                result=self.chain(n-1,self.socket(len(self.p)-1,1-e),route,sector)
                if result is not None:return result
        del self.p[before:];return None
    def build(self,seed):
        start=(self.c['start_position'],self.c['start_normal'],-1)
        for attempt in range(80):
            self.p=[];self.counts=[];self.random=Rand(seed+attempt*7919);self.budget=2500
            n=self.random.range(self.c['min_rooms'],self.c['max_rooms']);self.counts.append(n)
            s=self.chain(n,start,'Approach')
            if s is None:continue
            s=self.corridor(self.c['group_links'],s,'Approach')
            if s is None or not self.place('Junction',self.fit('Junction',0,s),'Junction',-2,s[2]):continue
            hub=len(self.p)-1;b=self.p[hub]['bounds'];center=((b['min'][0]+b['max'][0])/2,(b['min'][1]+b['max'][1])/2,0)
            exits=[];directions=[]
            for port in (1,2,3):
                s=self.socket(hub,port);directions.append(s[1]);s=self.corridor(self.c['branch_links'],s,'Route'+str(port))
                if s is None:break
                exits.append(s)
            if len(exits)<3:continue
            good=True
            for i in range(3):
                route='Route'+str(i+1);n=self.random.range(self.c['min_rooms'],self.c['max_rooms']);self.counts.append(n)
                s=self.chain(n,exits[i],route,(center,directions[i]))
                if s is None:good=False;break
                s=self.corridor(self.c['group_links'],s,route)
                if s is None or not self.place('RouteEnd',self.fit('RouteEnd',0,s),route,-2,s[2]):good=False;break
            if good:self.attempt=attempt;return True
        return False
    def add_treasure(self,seed):
        r=Rand(seed^0x54A391)
        for owner in range(len(self.p)):
            parent=self.p[owner];m=parent['module']
            if m not in self.combat:continue
            self.rolls+=1
            if r.fraction()>=self.c.get('treasure_chance_per_room',0):continue
            self.hits+=1;sides=self.modules[m].get('side_sockets',[]);choices=list(range(len(sides)));r.shuffle(choices);before=len(self.p)
            for side in choices:
                del self.p[before:];p=sides[side];s=(transform(p['position'],parent['t']),rot(p['normal'],parent['t'][1]),owner)
                route=parent['route']+'_Treasure'+str(owner)
                if not self.place('TreasureLink',self.fit('TreasureLink',0,s),route,-2,owner):continue
                s=self.socket(len(self.p)-1,1)
                if not self.place('Treasure',self.fit('Treasure',0,s),route,-2,s[2]):continue
                parent['side']=side;self.treasure+=1;break
            if parent['side']<0:del self.p[before:]
    def graph(self):
        nodes=[];connections=[];ports=[]
        for i,p in enumerate(self.p):
            node=dict(id=i,module=p['module'],origin=p['t'][0],yaw=p['t'][1],route=p['route'])
            if p['side']>=0:node['side_socket']=self.modules[p['module']]['side_sockets'][p['side']]['id']
            nodes.append(node)
            for n in range(len(self.ports(i))):
                s=self.socket(i,n)
                for j,b,other in ports:
                    if j!=i and all(abs(x-y)<=1 for x,y in zip(s[0],other[0])) and sum(x*y for x,y in zip(s[1],other[1]))<-.99:
                        connections.append({'from':j,'from_port':b,'to':i,'to_port':n})
                ports.append((i,n,s))
        return {'nodes':nodes,'connections':connections,'treasure_rooms':self.treasure}

def evaluate(p):
    g=p.graph();linked=set();sizes=[];degree=collections.Counter();used=collections.Counter()
    for e in g['connections']:
        a,b=e['from'],e['to'];linked.add((min(a,b),max(a,b)));degree[a]+=1;degree[b]+=1
        used[a,e['from_port']]+=1;used[b,e['to_port']]+=1
        pa=p.ports(a)[e['from_port']];pb=p.ports(b)[e['to_port']]
        if 'width' in pa and 'width' in pb and (abs(pa['width']-pb['width'])>1 or abs(pa['height']-pb['height'])>1):
            sizes.append({'a':a,'b':b,'modules':[p.p[a]['module'],p.p[b]['module']],'apertures':[[pa['width'],pa['height']],[pb['width'],pb['height']]]})
    seen={0}
    while True:
        old=len(seen)
        for a,b in linked:
            if a in seen or b in seen:seen.update((a,b))
        if len(seen)==old:break
    clashes=[]
    for i,a in enumerate(p.p):
        for j,b in enumerate(p.p[:i]):
            if (j,i) in linked:continue  # Adjacent pieces intentionally overlap at thick doorway seams.
            if any(overlap(c,d) for c in a['cells'] for d in b['cells']):clashes.append([j,i,b['module'],a['module']])
    unmatched=[]
    for i in range(len(p.p)):
        for n in range(len(p.ports(i))):
            if used[i,n]==0:
                s=p.socket(i,n)
                if not all(abs(a-b)<=1 for a,b in zip(s[0],p.c['start_position'])):unmatched.append([i,n,p.p[i]['module']])
    return dict(connected=len(seen)==len(p.p),non_neighbor_cell_overlaps=clashes,door_size_mismatches=sizes,
                unmatched_ports=unmatched,multi_matched_ports=[list(k) for k,v in used.items() if v>1])

def main():
    editor=read(OUT/'editor-state.json');c=json.loads(editor['generators'][0]['module_catalog_json']);live=json.loads(editor['generators'][0]['layout_manifest_json'])
    report={'method':'Offline FPlan model; exact UE RandomStream; no PIE or physical traversal','active_modules':[m['id'] for m in c['modules']],
       'active_room_ids':c.get('room_ids',['Distribution','Drainage','ShoredBreach'])}
    p=Plan(c);assert p.build(92247);p.add_treasure(92247);g=p.graph()
    same=len(g['nodes'])==len(live['nodes']) and g['connections']==live['connections']
    errors=[]
    for a,b in zip(g['nodes'],live['nodes']):
        if any(a[k]!=b[k] for k in ('module','route')) or any(abs(x-y)>.01 for x,y in zip(a['origin'],b['origin'])) or abs((a['yaw']-b['yaw']+180)%360-180)>.001:errors.append([a,b])
    report['engine_seed92247_match']=same and not errors;report['engine_graph_nodes']=len(live['nodes']);report['engine_graph_connections']=len(live['connections']);report['model_differences']=errors[:3]
    report['current_layout']=evaluate(p)
    if not report['engine_seed92247_match']:
        (OUT/'layout-probe.json').write_text(json.dumps(report,indent=2));raise RuntimeError('Model does not match saved engine layout')
    extension=read(SNAP/'SourceAssets/DungeonVentFreight20260922/Config/modules.json')
    future=copy.deepcopy(c);ids=set(extension['room_ids']);future['modules']=[m for m in future['modules'] if m['id'] not in ids]+extension['modules'];future['room_ids']=list(dict.fromkeys(report['active_room_ids']+extension['room_ids']))
    report['sweeps']={}
    for name,catalog in [('active_three_rooms',c),('candidate_five_rooms_not_installed',future)]:
        results={'seeds':200,'failed_seeds':[],'invariant_failures':[],'rooms':collections.Counter(),'attempt_histogram':collections.Counter(),'treasure_rolls':0,'treasure_hits':0,'treasure_placed':0,'size_mismatch_layouts':0};started=time.time()
        for seed in range(200):
            p=Plan(catalog)
            if not p.build(seed):results['failed_seeds'].append(seed);continue
            p.add_treasure(seed);e=evaluate(p)
            if not e['connected'] or e['non_neighbor_cell_overlaps'] or e['unmatched_ports'] or e['multi_matched_ports']:
                results['invariant_failures'].append({'seed':seed,**{k:v for k,v in e.items() if k!='door_size_mismatches'}})
            results['size_mismatch_layouts']+=bool(e['door_size_mismatches']);results['attempt_histogram'][p.attempt]+=1
            results['rooms'].update(x['module'] for x in p.p if x['module'] in p.combat)
            for dest,src in [('treasure_rolls','rolls'),('treasure_hits','hits'),('treasure_placed','treasure')]:results[dest]+=getattr(p,src)
        results['seconds']=round(time.time()-started,3);report['sweeps'][name]=results
        print(name,json.dumps(results),flush=True)
    (OUT/'layout-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
