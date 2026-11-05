"""Exit underneath the stock before crossing the rail to the shooting grip."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'pose composition','exec'))
import copy
FPS=240
source=json.load(gzip.open(O/'contact_fit_patch.json.gz','rt'))
final={};report={'profiles':{}};exported={}
owned=['clavicle_r',*[n for n in names if under(n,'upperarm_r')],'ik_hand_r']
thumb_offsets=json.loads((O/'thumb_return_offsets.json').read_text()) if (O/'thumb_return_offsets.json').exists() else {}
stable_palm=Vector(json.loads((O/'stable_palm_return.json').read_text())) if (O/'stable_palm_return.json').exists() else Vector()

def release_offset(t,kind):
    entry=smooth((t-.085)/.022)*(1-smooth((t-.117)/.023))
    exit=smooth((t-.419)/.047)*(1-smooth((t-.503)/.046))
    # Present the open hand to the outside flank of the independent grip.
    return_side=smooth((t-.622)/.024)*(1-smooth((t-.656)/.028))
    settle=smooth((t-.681)/.016)*(1-smooth((t-.705)/.025))
    travel=Vector(((9. if kind=='stable' else 4.)*return_side+3.*settle,0.,-45.*entry-77.*exit))
    if kind=='stable':travel+=stable_palm*smooth((t-.622)/.022)*(1-smooth((t-.673)/.021))
    return travel*.001

def move_hand(row,delta):
    if delta.length<1e-9:return row
    out=clone(row);S0=row['upperarm_r'].translation;E0=row['lowerarm_r'].translation;H0=row['hand_r'].translation
    u0=E0-S0;f0=H0-E0;H=H0+delta;reach=H-S0
    if reach.length>.99*(u0.length+f0.length):
        H=S0+reach.normalized()*.99*(u0.length+f0.length);delta=H-H0;reach=H-S0
    direction=reach.normalized();along=(u0.length_squared-f0.length_squared+reach.length_squared)/(2*reach.length)
    center=S0+direction*along;pole=E0-center;pole-=direction*pole.dot(direction)
    E=center+pole.normalized()*math.sqrt(max(0.,u0.length_squared-along*along))
    du=u0.rotation_difference(E-S0);dl=f0.rotation_difference(H-E)
    for n in owned:
        if under(n,'hand_r') or n=='ik_hand_r':out[n].translation+=delta
        elif n!='clavicle_r':
            upper=n.startswith('upperarm');pivot=S0 if upper else E0;end=S0 if upper else E
            rot=du if upper else dl;p=end+rot@(row[n].translation-pivot)
            out[n]=Matrix.LocRotScale(p,rot@row[n].to_quaternion(),row[n].to_scale())
    return out

def open_fingers(row,t,kind):
    # Open the hooked fingertips before lowering the palm past the rail.
    spread=smooth((t-.099)/.015)*(1-smooth((t-.130)/.017))
    spread+=smooth((t-.400)/.028)*(1-smooth((t-.468)/.032))
    thumb_return=smooth((t-.626)/.018)*(1-smooth((t-.668)/.016))
    index_return=smooth((t-.683)/.014)*(1-smooth((t-.703)/.018))
    gun=row['WPN_root']@rest['WPN_root'].inverted()
    for digit in ('index','middle','ring','pinky','thumb'):
        if digit=='thumb':
            offset=Vector(thumb_offsets.get(kind,[0.,0.,0.]))
            offset*=thumb_return
        else:
            offset=Vector((15. if digit=='index' else 9.,2.,5.))*spread
            if digit=='index' and kind in ('Default','phantom'):offset+=Vector((0.,0.,8.))*index_return
        if offset.length<.001:continue
        root=f'{digit}_01_r';tip=f'{digit}_03_r';pivot=row[root].translation
        axis=row[tip].translation-pivot;aim=axis+gun.to_3x3()@offset*.001
        rotation=axis.rotation_difference(aim)
        for n in (root,f'{digit}_02_r',tip):
            m=row[n];row[n]=Matrix.LocRotScale(pivot+rotation@(m.translation-pivot),rotation@m.to_quaternion(),m.to_scale())

for family,clip in source.items():
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    current=copy.deepcopy(clip);tracks={tr['bone']:tr for tr in current['tracks'] if tr['bone'] in owned};rows=[]
    for i in range(217):
        t=i/FPS;row,_=compose(clip,t);offset=release_offset(t,kind)
        if .08<t<.74:
            gun=row['WPN_root']@rest['WPN_root'].inverted();row=move_hand(row,gun.to_3x3()@offset)
            open_fingers(row,t,kind)
            for n,tr in tracks.items():
                p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
                a=tr['values'][i*10+3:i*10+7]
                if dq.dot(Quaternion((a[3],*a[:3])))<0:dq.negate()
                tr['values'][i*10:i*10+10]=[*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)]
        if family=='skeleton_mag10_stable' and 0<i<216:
            # Both magazines use the same physical rear grip and matched idle
            # hand pose. Carry the seated right branch in weapon space, leaving
            # the extended-magazine gun, torso, and left support tracks intact.
            donor=final['skeleton_base_stable'][i];transfer=row['WPN_root']@donor['WPN_root'].inverted()
            for n in owned:row[n]=transfer@donor[n]
            for n,tr in tracks.items():
                p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
                a=tr['values'][i*10+3:i*10+7]
                if dq.dot(Quaternion((a[3],*a[:3])))<0:dq.negate()
                tr['values'][i*10:i*10+10]=[*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)]
        rows.append(row)
    final[family]=rows;exported[family]=current;print('UNDER_STOCK_ARC',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(exported,fp,separators=(',',':'))
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend').replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216').replace("O/'authoring.json'","O/'release_arc_export.json'")
exec(compile(code,'native editable export','exec'))
print('M24_UNDER_STOCK_ARC_COMPLETE',flush=True)
