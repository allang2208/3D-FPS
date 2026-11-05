"""Seat the articulated hand as a unit with a small, continuous shoulder offset.

The fingers have already been shaped around the stock. A rigid translation of
the right branch allows the soft surface to clear the frame without introducing
new wrist rotation, finger curl, or a change in forearm length.
"""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'native surfaces','exec'))
import copy

FPS=240
patch=json.load(gzip.open(O/'digit_path_patch.json.gz','rt'))
ids=np.unique(np.r_[hand_ids[::2],hand_ids[::3],arm_ids[::8],arm_ids[::15]])
sample_times=[i/120 for i in range(109)]
final={}
report={'profiles':{},'offset_units':'mm in gun coordinates'}
exported={}

def active_points(tree, row):
    points=skin_points(row,ids,True)
    inv=rest['WPN_root']@row['WPN_root'].inverted()
    points=(np.c_[points,np.ones(len(points))]@np.asarray(inv).T)[:,:3]
    return [Vector(p) for p in points if tree.find_nearest(Vector(p))[3]<.012]

def inside_constraints(tree, points, offset):
    translation=offset*.001
    contacts=[]
    for point in points:
        position=point+translation
        surface,_,_,distance=tree.find_nearest(position)
        if distance<.00008:continue
        votes=0
        for direction in rays:
            hit,normal,_,_=tree.ray_cast(position,direction)
            votes+=hit is not None and normal.dot(direction)>0
        if votes<2:continue
        if signed_distance(tree,[position],True)[0]<0:
            contacts.append(((surface-position).normalized(),distance*1000))
    return contacts

def fit_offset(tree,points,seed,limit):
    def measure(offset):
        pairs=inside_constraints(tree,points,offset)
        worst=max([d for _,d in pairs],default=0.)
        return 16*worst**2+sum(d*d for _,d in pairs)/max(1,len(pairs))+.025*offset.length_squared+.025*(offset-seed).length_squared,pairs
    def bounded(v):return v.normalized()*limit if v.length>limit else v
    best=bounded(seed);score,pairs=measure(best)
    for _ in range(5):
        if not pairs:break
        target,depth=max(pairs,key=lambda p:p[1])
        if depth<.23:break
        mean=sum((n*(d*d) for n,d in pairs),Vector()).normalized()
        proposals=[bounded(best+n*step) for n in (target,mean) for step in (depth+.25,depth*.55)]
        improved=False
        for trial in proposals:
            cost,contacts=measure(trial)
            if cost<score:best,score,pairs,improved=trial,cost,contacts,True
        if not improved:break
    return best

def solve_path(tree,clip):
    route=[]
    for i,t in enumerate(sample_times):
        if i==0 or i==len(sample_times)-1:
            route.append(Vector());continue
        row,_=compose(clip,t)
        limit=8.*smooth(t/.025)*smooth((.9-t)/.025)
        seed=route[-1]*.8
        route.append(fit_offset(tree,active_points(tree,row),seed,limit))
    # Keep a stable contact anchor through impact. Blend neighboring controls to
    # avoid frame-to-frame chatter at either side of the contact plateau.
    averaged=[v.copy() for v in route]
    for i in range(1,len(route)-1):
        averaged[i]=route[i]*.72+(route[i-1]+route[i+1])*.14
    hold=route[30]
    for i,t in enumerate(sample_times):
        weight=smooth((t-.14)/.02)*smooth((.46-t)/.015)
        averaged[i]=averaged[i].lerp(hold,weight)
    return averaged

def interpolate(path,t):
    key=t*120
    i=min(int(key),len(path)-2)
    return path[i].lerp(path[i+1],key-i)

for family,clip in patch.items():
    variant=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    tree=weapon_tree(variant,'mag10' if 'mag10' in family else 'mag5')
    route=solve_path(tree,clip)
    rows=[]
    current=copy.deepcopy(clip)
    translations={n:next(tr for tr in current['tracks'] if tr['bone']==n) for n in ('clavicle_r','ik_hand_r')}
    for i in range(217):
        t=i/FPS;row,_=compose(clip,t)
        gun=row['WPN_root']@rest['WPN_root'].inverted()
        offset=gun.to_3x3()@interpolate(route,t)*.001
        for n in ['clavicle_r',*RIGHT,'ik_hand_r']:
            row[n].translation+=offset
        for n,tr in translations.items():
            position=(K@local(row,n)@K).translation-raw(D['clips'][clip['base']],t,n).translation
            tr['values'][i*10:i*10+3]=list(position)
        rows.append(row)
    final[family]=rows;exported[family]=current
    report['profiles'][family]={'max_offset_mm':max(v.length for v in route),'offsets':[list(v) for v in route]}
    print('RIGHT_PALM_SEATED',family,report['profiles'][family]['max_offset_mm'],flush=True)

with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(exported,fp,separators=(',',':'))
(O/'palm_path.json').write_text(json.dumps(report,indent=2))
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend').replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216').replace("O/'authoring.json'","O/'palm_path_export.json'")
exec(compile(code,'native editable export','exec'))
print('M24_RIGHT_PALM_SEAT_COMPLETE',flush=True)
