"""Fit the brief cocking regrip without driving the palm through the frame."""
import bpy,json,sys,math,numpy as np,time
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;sys.path.insert(0,str(O))
from cock_fit_geometry import context,solid,skin,inside_depth
family=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
c=context(family);g=c['scope'];base=c['base'];side=c['side'];sign=1 if side=='r' else -1
chain=[n for n in g['names'] if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
pad=g['pad'];hold=g['hold_pads'];index=g['index_pad'];pivot=Vector((0,.153,-.033))
ph='WPN_Hammer';hp=g['parents'][ph]
samples=(0.,.5,1.)
local_hammer=base[hp].inverted()@base[ph]
entries={k:solid([base[hp]@local_hammer@Matrix.Rotation(g['COCK']*k,4,'X')@v for v in c['hammer_local']],c['hammer_faces']) for k in samples}
sample_ids=list(range(len(c['coords'])))
distal={}
for digit in ('middle','ring','pinky','thumb'):
    n=digit+'_03_'+side;ids=[i for i,label in enumerate(c['labels']) if label==n]
    ids.sort(key=lambda i:(c['bind'][n]@c['coords'][i])[1]);distal[digit]=ids[-max(1,len(ids)//3):]

def pose(xx,cock):
    p={n:m.copy() for n,m in base.items()}
    turn=Matrix.Rotation(xx[3],4,'X')@Matrix.Rotation(xx[4],4,'Y')@Matrix.Rotation(xx[5],4,'Z')
    delta=Matrix.Translation(Vector(xx[:3]))@Matrix.Translation(pivot)@turn@Matrix.Translation(-pivot)
    g['arm_at'](p,base,side,delta@base['hand_'+side])
    p[ph]=base[hp]@local_hammer@Matrix.Rotation(g['COCK']*cock,4,'X')
    errors={}
    for j,(digit,held_pad) in enumerate(hold.items()):
        target=base[digit+'_03_'+side]@held_pad+Vector((sign*xx[6],xx[7],xx[8]))+Vector(xx[9+j*3:12+j*3])
        errors[digit]=g['finger_at'](p,side,held_pad,target,1.,digit)*1000
    target=p[ph]@g['spur_local']+Vector((sign*.0035+xx[18],.0015+xx[19],.008+xx[20]))
    errors['thumb']=g['finger_at'](p,side,pad,target,1.)*1000
    # The released index remains on the outside of the frame during cocking.
    target=base['index_03_'+side]@index+Vector((sign*xx[6],xx[7],xx[8]))
    errors['index']=g['finger_at'](p,side,index,target,1.,'index')*1000 if side=='r' else 0.
    return p,errors

def evaluate(xx,full=False):
    maximum=0.;average=0.;reach=0.;contact=0.;records=[]
    for cock in samples:
        p,errors=pose(xx,cock);points=skin(c,p);ids=range(len(points)) if full else sample_ids;depths=[]
        solids=list(c['solids'].values())+[entries[cock]]
        for i in ids:depths.append(max(inside_depth(Vector(points[i]),entry) for entry in solids))
        maximum=max(maximum,max(depths));average+=sum(max(0,v-.3)**2 for v in depths)/len(depths)
        reach+=sum(v*v for n,v in errors.items())
        gaps={digit:min((entries[cock][0] if digit=='thumb' else c['solids']['9_l'][0]).find_nearest(Vector(points[i]))[3]*1000 for i in ids) for digit,ids in distal.items()}
        contact+=sum(max(0,v-.8)**2 for v in gaps.values())
        if full:
            worst=max(range(len(depths)),key=lambda i:depths[i]);records.append(dict(cock=cock,maximum_mm=max(depths),worst_bone=c['labels'][worst],over_1mm=sum(d>1 for d in depths),fingertip_error_mm=errors,grip_skin_gap_mm=gaps))
    regular=.035*sum((v*1000)**2 for v in xx[:3])+.006*sum(math.degrees(v)**2 for v in xx[3:6])+.01*sum((v*1000)**2 for v in xx[6:])
    score=maximum**2*350+average*350+reach*22+contact*12+regular
    return (score,records) if full else score

x=[-sign*.025,-.020,.030,math.radians(7),0.,0.,0.,0.,0.]+[0.]*12
contract_file=O/('cock_contact_'+family+'.json')
if contract_file.exists():
    previous=json.loads(contract_file.read_text());x[:9]=previous['hand_translation_canonical']+previous['wrist_rotation_xyz']+[previous['grasp_target_translation_canonical'][0]*sign,*previous['grasp_target_translation_canonical'][1:]]
    for j,digit in enumerate(hold):x[9+j*3:12+j*3]=previous.get('digit_target_offsets',{}).get(digit,[0.,0.,0.])
    x[18:21]=list(Vector(previous['thumb_center_offset_canonical'])-Vector((sign*.0035,.0015,.008)))
print('COCK_START',family,evaluate(x,True),flush=True)
best=evaluate(x)
for level in range(6):
    distance=.004*(.62**level);angle=math.radians(5)*(.62**level)
    for sweep in range(3):
        changed=False
        for i in range(len(x)):
            step=angle if 3<=i<6 else distance;value=x[i];score=best
            for direction in (-1,1):
                candidate=x[:];candidate[i]+=step*direction
                limit=math.radians(30) if 3<=i<6 else (.012 if i>=6 else .05)
                if abs(candidate[i])>limit:continue
                result=evaluate(candidate)
                if result<score:score=result;value=candidate[i]
            if value!=x[i]:x[i]=value;best=score;changed=True
        if not changed:break
    print('COCK_FIT_LEVEL',family,level,round(best,2),x,flush=True)
score,records=evaluate(x,True)
contract=dict(family=family,index_release='follow_hand' if side=='l' else 'held_contact',hand_translation_canonical=x[:3],wrist_rotation_xyz=x[3:6],grasp_target_translation_canonical=[sign*x[6],x[7],x[8]],digit_target_offsets={digit:x[9+j*3:12+j*3] for j,digit in enumerate(hold)},thumb_center_offset_canonical=[sign*.0035+x[18],.0015+x[19],.008+x[20]],samples=records,score=score)
(O/('cock_contact_'+family+'.json')).write_text(json.dumps(contract,indent=2))
print('COCK_FIT_DONE',family,json.dumps(contract),flush=True)
