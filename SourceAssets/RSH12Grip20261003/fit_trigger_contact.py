"""Place the native index pad against the trigger through the open guard."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O))
from cock_fit_geometry import context,solid,skin,inside_depth
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['single','idle']
family,kind=args;c=context(family);g=c['scope'];base=c['base'];side=c['side'];sign=1 if side=='r' else -1
if kind=='aim':
    entry=next(e for e in g['PROFILE']['clips'] if e['kind']=='aim')
    native=g['native_pose'](g['apply_profile']({n:g['matrix'](v) for n,v in g['D']['clips']['aim']['samples'][0]['local'].items()},entry))
    inverse=(native['WPN_root']@g['alignment']).inverted();base={n:inverse@m for n,m in native.items()}
trigger=base['WPN_Trigger']@Matrix.Rotation(math.radians(-7),4,'X')
raw=json.loads((g['B']/'canonical_parts.json').read_text());part=next(p for p in raw if p['name']=='17_l')
bind=Matrix(g['META']['mechanical_bind_matrices']['WPN_Trigger']).inverted()@g['root_rest']@g['alignment']
shape=solid([trigger@bind@Vector(v) for v in part['verts']],part['faces']);solids=list(c['solids'].values())+[shape]
ids=[i for i,label in enumerate(c['labels']) if label.startswith('index_')];distal=[i for i in ids if c['labels'][i]=='index_03_'+side]
distal.sort(key=lambda i:(c['bind']['index_03_'+side]@c['coords'][i])[1]);distal=distal[-max(1,len(distal)//3):]

def evaluate(x,full=False):
    p={n:m.copy() for n,m in base.items()};error=g['finger_at'](p,side,g['index_pad'],Vector(x),1.,'index',metacarpal=True)*1000
    points=skin(c,p);depths=[max(inside_depth(Vector(points[i]),s) for s in solids) for i in ids]
    gap=min(shape[0].find_nearest(Vector(points[i]))[3]*1000 for i in distal)
    score=max(depths)**2*400+sum(v*v for v in depths)*2+max(0,gap-.5)**2*30+error**2*30
    return (score,max(depths),gap,error) if full else score

x=[-sign*.014,.079,.008];score=evaluate(x)
for level in range(6):
    step=.006*(.55**level)
    for _ in range(3):
        changed=False
        for i in range(3):
            best=x[i];value=score
            for direction in (-1,1):
                candidate=x[:];candidate[i]+=direction*step
                if not .006<=-sign*candidate[0]<=.04 or not .06<=candidate[1]<=.125 or not -.015<=candidate[2]<=.03:continue
                cost=evaluate(candidate)
                if cost<value:best=candidate[i];value=cost
            if best!=x[i]:x[i]=best;score=value;changed=True
        if not changed:break
score,maximum,gap,error=evaluate(x,True)
recipe=dict(family=family,kind=kind,offset_canonical=list(Vector(x)-base['WPN_Trigger'].translation),index_skin_penetration_mm=maximum,index_skin_trigger_gap_mm=gap,index_center_error_mm=error)
(O/('trigger_contact_'+family+'_'+kind+'.json')).write_text(json.dumps(recipe,indent=2));print('TRIGGER_CONTACT_FITTED',json.dumps(recipe),flush=True)
