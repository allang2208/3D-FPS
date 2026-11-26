"""Rebuild sleeves from current native arms with stable, paired wrist bands."""
import ast,sys,copy,json,math,hashlib,bpy,bmesh,numpy as np
from pathlib import Path
from mathutils import Vector,kdtree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import P,R,C,read,write,unit,normals,smooth,settle,cuff_weights
from combat2_details import sew
def build(rig):
    rows=read(C/'captured.json')['rows'];row=next(r for r in rows if r['key']=='Native_'+rig);native=read(row['file']);prototype=read(R/'Authored'/f'shirt_fp_{rig}.json');temp=C/'Authored/NativeBlank';temp.mkdir(exist_ok=True)
    source=(P/'Tools/ST6SleeveRepair/author.py').read_text(encoding='utf-8');tree=ast.parse(source);code='\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','smooth','normals','build'])
    # Keep the original anatomical cuff; only the free sleeve gets extra ease.
    code=code.replace('0.34 + 0.25 * (1 - cuff) + folds','0.34 + 0.75 * (1 - cuff)').replace('along / 25','along / 8').replace('coords[:, 0] *= 1.5','coords[:, 0] *= 4.6875').replace('dist[face] / 25','dist[face] / 8').replace('length / 25','length / 8').replace('thickness / 25','thickness / 8')
    ns=dict(json=json,copy=copy,math=math,hashlib=hashlib,Path=Path,bpy=bpy,bmesh=bmesh,np=np,Vector=Vector,read=read,OUT=temp);exec(compile(code,'current_native_cuff_cut','exec'),ns);ns['build'](dict(profile=rig,file=row['file']))
    d=read(temp/(rig+'.json'));byname={b['name']:b['index'] for b in prototype['bones']};delta=max(np.linalg.norm(np.array(native['bones'][name]['position'])-b['position']) for b in prototype['bones'] if (name:=b['name']) in native['bones'] and name.startswith(('upperarm','lowerarm','hand_')))
    if delta>.01:raise RuntimeError('Native arm bind changed: '+rig+' '+str(delta))
    d['bones']=prototype['bones'];d['source']=prototype['source'];d['rig']=rig;d['weights']=[[[byname[n],w] for n,w in ws.items()] for ws in d['weights']];d['material_slots']=['CombatRipstop','CombatCuff','CombatLining'];dest='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/';d['materials']=[dest+'M_'+m for m in d['material_slots']]
    p=np.array(d['positions']);f=np.array(d['triangles']);outerids=np.concatenate([np.arange(part['first_vertex'],part['first_vertex']+part['vertices']//2) for part in d['parts']]);remap=np.full(len(p),-1,dtype=int);remap[outerids]=np.arange(len(outerids));tri=remap[f[(remap[f]>=0).all(1)]];q=p[outerids].copy();pins=np.zeros(len(q));cuff_records={}
    for part in d['parts']:
        side=part['name'][-1];start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);bones=native['bones'];w=np.array(bones['hand_'+side]['position']);axis=unit(w-np.array(bones['lowerarm_'+side]['position']));dist=-(p[ids]-w)@axis;cuff_weights(d,ids,dist,side)
        for a,b in zip(ids,ids+count):d['weights'][b]=copy.deepcopy(d['weights'][a])
        pins[remap[ids]]=1-smooth((dist-4.4)/3.0);cuff_records[side]=dict(native_cut_from_wrist_cm=1.,fixed_band_to_cm=4.4,weight_transition_to_cm=7.,hand_weight_at_rim=.16)
    edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),1);edges,n=np.unique(edges,axis=0,return_counts=True);border=np.unique(edges[n==1]);kd=kdtree.KDTree(len(border))
    for i,vi in enumerate(border):kd.insert(Vector(q[vi]),i)
    kd.balance();pins=np.maximum(pins,np.array([1-smooth((kd.find(Vector(v))[2]-.7)/2) for v in q]));pins[border]=1
    moved=settle('FP_'+rig,q,tri,pins,native,frames=36);new=p.copy();new[outerids]=moved;normal=normals(moved,tri)
    for part in d['parts']:
        start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);local=remap[ids];new[ids+count]=moved[local]-normal[local]*.12
    d['positions']=new.tolist();d['normals']=normals(new,f)[f].tolist();sew(d);d['materials']=[m.replace('CombatShirtR2','CombatShirtR3') for m in d['materials']];d['cloth_production']=dict(method='Current native arms; unchanged wrist targets; free sleeve spring-length allowance',native_sha256=row['sha256'],cuffs=cuff_records,paired_facing_weights=True,runtime_simulation=False);file=C/'Authored'/f'shirt_fp_{rig}.json';write(file,d);print('NATIVE_CUFF_REPAIRED',rig,len(d['triangles']),flush=True);return dict(rig=rig,file=str(file),native=d['source'])
if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:];rigs=args[0].split(',');results=[]
    for rig in rigs:results.append(build(rig))
    write(C/('fp-batch-'+args[1]+'.json'),dict(completed=True,rows=results))
