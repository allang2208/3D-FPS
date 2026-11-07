"""Re-seat both stock power grips while retaining gun path and action clock."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'pose helpers','exec'))
import copy
tree=ast.parse((S/'M24QuickMeleeRightHandR3_20261104/release_arc.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='move_hand')),'fixed-length chain transport','exec'))
owned=['clavicle_r',*[n for n in names if under(n,'upperarm_r')],'ik_hand_r']
contact=json.loads((O/'contact.json').read_text());ref,_=compose(entry('skeleton_base','quick_melee'),.25)
refroot=rest['WPN_root']@ref['WPN_root'].inverted()
delta=Matrix(contact['hand'])@(refroot@ref['hand_r']).inverted()
digit_delta={n:Quaternion(q)@local(ref,n).to_quaternion().inverted() for n,q in contact['rotations'].items()}
FPS=240;times=[i/FPS for i in range(217)];patch={}
def weight(t):return smooth((t-.085)/.065)*(1-smooth((t-.40)/.16))

for family in D['profiles']:
    if not family.startswith('skeleton_'):continue
    clip=entry(family,'quick_melee');tracks={n:[] for n in owned};last={}
    idle,_=compose(entry(family,'idle'),0.)
    idle_hand=idle['WPN_root'].inverted()@idle['hand_r']
    for t in times:
        original,_=compose(clip,t);row=clone(original);w=weight(t)
        if w>1e-7:
            root=original['WPN_root']@rest['WPN_root'].inverted()
            change=root@lerp(Matrix.Identity(4),delta,w)@root.inverted()
            target=change@original['hand_r']
            held=smooth((t-.13)/.02)*(1-smooth((t-.40)/.025))
            target=lerp(target,root@Matrix(contact['hand']),held)
            row=move_hand(original,target.translation-original['hand_r'].translation)
            row['hand_r']=target
            for n in names:
                if n=='hand_r' or not under(n,'hand_r'):continue
                p,q,s=local(original,n).decompose()
                if n in digit_delta:q=Quaternion().slerp(digit_delta[n],w)@q
                if n in contact['rotations']:q=q.slerp(Quaternion(contact['rotations'][n]),held)
                row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
            row['ik_hand_r']=target.copy()
        settle=smooth((t-.72)/.12)
        if settle>1e-7:
            previous=clone(row)
            target=lerp(row['hand_r'],row['WPN_root']@idle_hand,settle)
            row=move_hand(row,target.translation-row['hand_r'].translation)
            row['hand_r']=target
            for n in names:
                if n=='hand_r' or not under(n,'hand_r'):continue
                value=lerp(local(previous,n),local(idle,n),settle)
                row[n]=row[parents[n]]@value
            row['ik_hand_r']=target.copy()
        for n in owned:
            p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)])
    replace={n:{'bone':n,'times':times,'values':v} for n,v in tracks.items()}
    result=copy.deepcopy(clip);result['tracks']=[replace.pop(tr['bone'],tr) for tr in clip['tracks']]+list(replace.values());patch[family]=result
    print('STOCK_CONTACT_AUTHORED',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))
print('STOCK_CONTACT_PATCH_READY',flush=True)
