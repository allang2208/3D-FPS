"""Apply the same fixed-wrist repair to both full-body shirt sources."""
import sys,copy,numpy as np
from pathlib import Path
from mathutils import Vector,kdtree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import P,R,C,read,write,unit,normals,smooth,settle,cuff_weights
T=P/'Tools/ModernTacticalSet'
code=(T/'combat3_shirt_blank.py').read_text(encoding='utf-8');ns={'__name__':'cuff_blank','__file__':str(T/'combat3_shirt_blank.py')};code=code.replace("exec(compile(code,", "code=code.replace(\"R=S/'CombatShirtR3'\",\"R=S/'CombatShirtR3/CuffRepairR1'\")\nexec(compile(code,");exec(compile(code,'fixed_cuff_blank','exec'),ns)
for rig in ['Jason','Kaitlin']:
    d=read(C/'Authored'/f'shirt_cloth_{rig}.json');body=read(C/'Inputs'/f'Body_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);count=len(p)//2;q=p[:count].copy();tri=f[(f<count).all(1)];bones={b['name']:np.array(b['position']) for b in d['bones']};names={b['index']:b['name'] for b in d['bones']};arm=np.array([sum(w for bi,w in ws if any(s in names[bi] for s in ['upperarm','lowerarm','hand_','twist'])) for ws in d['weights'][:count]]);pins=1-smooth((arm-.10)/.65)
    for side in ['l','r']:
        mass=np.array([sum(w for bi,w in ws if names[bi].endswith('_'+side) and names[bi].startswith(('upperarm','lowerarm','hand_'))) for ws in d['weights'][:count]]);ids=np.flatnonzero(mass>.5);w=bones['hand_'+side];axis=unit(w-bones['lowerarm_'+side]);dist=-(q[ids]-w)@axis;pins[ids]=np.maximum(pins[ids],1-smooth((dist-4.4)/3));cuff_weights(d,ids,dist,side)
    for i in range(count):d['weights'][i+count]=copy.deepcopy(d['weights'][i])
    edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),1);edges,n=np.unique(edges,axis=0,return_counts=True);border=np.unique(edges[n==1]);kd=kdtree.KDTree(len(border))
    for i,vi in enumerate(border):kd.insert(Vector(q[vi]),i)
    kd.balance();pins=np.maximum(pins,np.array([1-smooth((kd.find(Vector(v))[2]-.8)/2) for v in q]));pins[border]=1;moved=settle('Shirt_'+rig,q,tri,pins,body);nn=normals(moved,tri);thickness=np.linalg.norm(p[:count]-p[count:],axis=1);new=np.concatenate([moved,moved-nn*thickness[:,None]]);d['positions']=new.tolist();d['normals']=normals(new,f)[f].tolist();d['cloth_production']=dict(method='Fixed native cuff and torso anchors; free sleeve spring-length allowance',rest_shape_key=False,paired_facing_weights=True,runtime_simulation=False);write(C/'Authored'/f'shirt_cloth_{rig}.json',d)
code=(T/'combat3_details.py').read_text(encoding='utf-8').replace("R=S/'CombatShirtR3'", "R=S/'CombatShirtR3/CuffRepairR1'");exec(compile(code,'fixed_cuff_sewing','exec'),{'__name__':'__main__','__file__':str(T/'combat3_details.py')})
