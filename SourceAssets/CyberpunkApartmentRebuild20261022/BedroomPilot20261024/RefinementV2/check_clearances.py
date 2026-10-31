"""Saved asset checks: door sweeps, fabric separation and real support surfaces."""
from pathlib import Path
import json,math,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;D=R/'Audit/after'
data=json.loads((D/'components.json').read_text('utf8'))
rows=data['components'];raws={};world=[];trees=[];bounds=[]
candidate='candidate' in sys.argv
if candidate:
    shifts={'AP_Container_Bed2_Desk_Drawer':(8.,-8.,0.),'AP_Bed2_Chair':(0.,-14.,0.),'BP_Headphones':(0.,0.,-.25),'BP_DeskLife':(0.,0.,-.25),'BP_DeskRail':(0.,0.,-.25)}
    for row in rows:
        if row['actor'] in shifts:row['transform']['origin']=[p+d for p,d in zip(row['transform']['origin'],shifts[row['actor']])]
    for c in data.get('containers',[]):
        if c['actor'] in shifts:c['hinge_world']=[p+d for p,d in zip(c['hinge_world'],shifts[c['actor']])]
for row in rows:
    raw=raws.setdefault(row['key'],json.loads((D/(row['key']+'.json')).read_text('utf8')))
    t=row['transform'];o=t['origin'];a=t['axes']
    vs=[]
    for v in raw['vertices']:
        p=[(o[i]+sum(v[j]*a[j][i] for j in range(3)))/100 for i in range(3)]
        vs.append(Vector((p[0],-p[1],p[2])))
    fs=[tuple(reversed(t)) for t in raw['triangles'] if min(t)>=0]
    world.append((vs,fs));trees.append(BVHTree.FromPolygons(vs,fs,all_triangles=True))
    bounds.append(([min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]))

def overlaps(a,b):return min(min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) for i in range(3))>.00005

sweeps=[]
for c in data.get('containers',[]):
    idx=next(i for i,r in enumerate(rows) if r['actor']==c['actor'] and r['component']=='Door')
    vs,fs=world[idx];hinge=Vector((c['hinge_world'][0]/100,-c['hinge_world'][1]/100,c['hinge_world'][2]/100))
    step=max(1,math.ceil(abs(c['opened_yaw']))) if 'SWING' in c['motion'] else max(1,math.ceil(Vector(c['travel_world']).length))
    contacts={}
    for n in range(step+1):
        f=n/step
        if 'DRAWER' in c['motion']:
            travel=Vector((c['travel_world'][0]/100,-c['travel_world'][1]/100,c['travel_world'][2]/100))*f
            points=[v+travel for v in vs]
        else:
            angle=math.radians(-c['opened_yaw']*f);co,si=math.cos(angle),math.sin(angle);points=[]
            for v in vs:
                q=v-hinge;points.append(hinge+Vector((co*q.x-si*q.y,si*q.x+co*q.y,q.z)))
        box=([min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)])
        targets=[j for j,r in enumerate(rows) if j!=idx and r['actor']!=c['actor'] and not r['hidden'] and overlaps(box,bounds[j])]
        if not targets:continue
        tree=BVHTree.FromPolygons(points,fs,all_triangles=True)
        for j in targets:
            hits=tree.overlap(trees[j])
            if hits:contacts.setdefault(rows[j]['actor']+'/'+rows[j]['component'],[]).append(round(f,4))
    sweeps.append(dict(actor=c['actor'],motion=c['motion'],samples=step+1,contacts=contacts))
    print('BEDROOM_DOOR_SWEEP',c['actor'],step+1,len(contacts),flush=True)

internal=[]
for actor,first,second in [('BP_LaundryBasket',['FogLinen'],['Graphite','Walnut']),('AP_Bed2_Bed',['FogLinen'],['CharcoalWeave'])]:
    idx=next(i for i,r in enumerate(rows) if r['actor']==actor);r=rows[idx];raw=raws[r['key']];vs,_=world[idx]
    sets=[]
    for names in (first,second):
        faces=[tuple(reversed(f)) for f,m in zip(raw['triangles'],raw['materials']) if r['slots'][m] in names]
        if actor=='AP_Bed2_Bed' and names==first:
            # Sewn piping deliberately meets the duvet. Test the mattress/pillow
            # bodies separately using their connected surfaces, area and thickness.
            roots=list(range(len(vs)))
            def root(i):
                while roots[i]!=i:roots[i]=roots[roots[i]];i=roots[i]
                return i
            for f in faces:
                for v in f[1:]:roots[root(v)]=root(f[0])
            islands={}
            for f in faces:islands.setdefault(root(f[0]),[]).append(f)
            structural=[]
            structural_count=0
            for group in islands.values():
                ps=[vs[i] for f in group for i in f]
                area=sum((vs[f[1]]-vs[f[0]]).cross(vs[f[2]]-vs[f[0]]).length*.5 for f in group)
                span=[max(v[q] for v in ps)-min(v[q] for v in ps) for q in range(3)]
                if span[2]>.02 and area/max(span[0]*span[1],1e-9)>1.2:
                    structural.extend(group);structural_count+=1
            faces=structural
            print('BEDROOM_LINEN_BODIES',structural_count,len(faces),flush=True)
        sets.append(BVHTree.FromPolygons(vs,faces,all_triangles=True))
    hits=sets[0].overlap(sets[1]);internal.append(dict(actor=actor,surfaces=[first,second],triangle_intersections=len(hits)))
    print('BEDROOM_INTERNAL_SURFACES',actor,len(hits),flush=True)

supports=[]
for child,parent,zbase in [('BP_BedsideTray','AP_Container_Bed2_Nightstand_-1_1',None),('BP_BedsideBooks','AP_Container_Bed2_Nightstand_1_1',None),('BP_Headphones','AP_Bed2_Desk',None),('BP_DeskLife','AP_Bed2_Desk',None),('BP_BenchFoldedLinen','BP_WindowBench',None),('BP_Slippers','BP_BedRug',None),('BP_LaundryBasket','AP_Floor_Bed2',None)]:
    ci=next(i for i,r in enumerate(rows) if r['actor']==child);pi=next(i for i,r in enumerate(rows) if r['actor']==parent and r['component'] in ('StaticMeshComponent0','Body'))
    ps=world[ci][0];bottom=min(v.z for v in ps);samples=[v for v in ps if v.z<bottom+.00015];gaps=[]
    for p in samples[::max(1,len(samples)//40)]:
        hit=trees[pi].ray_cast(p+Vector((0,0,.003)),Vector((0,0,-1)),.12)
        if hit[0] is not None:gaps.append((p.z-hit[0].z)*1000)
    supports.append(dict(child=child,parent=parent,samples=len(gaps),minimum_gap_mm=min(gaps) if gaps else None,maximum_gap_mm=max(gaps) if gaps else None))
for child in ['AP_Bed2_Desk','AP_Bed2_Chair','AP_Bed2_Desk_PC','AP_Planter3']+[f'AP_Container_Bed2_Wardrobe_{i}' for i in range(1,5)]:
    ci=next(i for i,r in enumerate(rows) if r['actor']==child and r['component'] in ('StaticMeshComponent0','Body'));pi=next(i for i,r in enumerate(rows) if r['actor']=='AP_Floor_Bed2')
    ps=world[ci][0];bottom=min(v.z for v in ps);samples=[v for v in ps if v.z<bottom+.0001];gaps=[]
    for p in samples[::max(1,len(samples)//40)]:
        hit=trees[pi].ray_cast(p+Vector((0,0,.003)),Vector((0,0,-1)),.12)
        if hit[0] is not None:gaps.append((p.z-hit[0].z)*1000)
    supports.append(dict(child=child,parent='AP_Floor_Bed2',samples=len(gaps),minimum_gap_mm=min(gaps) if gaps else None,maximum_gap_mm=max(gaps) if gaps else None))

extra=[]
for actor,component,target in [('AP_Container_Bed2_Desk_Drawer','Body','AP_Bed2_Desk')]:
    i=next(i for i,r in enumerate(rows) if r['actor']==actor and r['component']==component)
    j=next(i for i,r in enumerate(rows) if r['actor']==target)
    extra.append(dict(a=actor+'/'+component,b=target,triangle_intersections=len(trees[i].overlap(trees[j]))))
result=dict(scope='Bedroom pilot Bed2 only; saved SourceModel LOD0 geometry',candidate=candidate,sweeps=sweeps,internal_surfaces=internal,support_surfaces=supports,static_extra=extra,
            movement_sampling='Swing at <=1 degree, drawer at <=1 cm; offline placement check, no gameplay started',game_run=False)
(D/('clearances-candidate.json' if candidate else 'clearances.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print('BEDROOM_CLEARANCE_CHECK_FINISHED')
