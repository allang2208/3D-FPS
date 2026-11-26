"""Sewn panel detail and real spaced topstitches on turned garment openings."""
import ast,sys,copy,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,unit,subset,merge
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR2';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR2'
def topstitch(d):
    p=np.array(d['positions']);count=len(p);faces=np.array(d['triangles']);outer_vertices=np.zeros(count,bool)
    if d.get('parts'):
        for part in d['parts']:outer_vertices[part['first_vertex']:part['first_vertex']+part['vertices']//2]=True
    else:outer_vertices[:count//2]=True
    outer=faces[outer_vertices[faces].all(1)];edges={};adj=[[] for _ in range(count)]
    normals=np.zeros((count,3))
    for f in outer:
        n=-np.cross(p[f[1]]-p[f[0]],p[f[2]]-p[f[0]]);center=p[f].mean(0)
        for v in f:normals[v]+=n;adj[v].append(center)
        for a,b in zip(f,np.roll(f,-1)):edges.setdefault(tuple(sorted([int(a),int(b)])),[]).append((int(a),int(b)))
    boundary=[row[0] for row in edges.values() if len(row)==1];neighbors={}
    for a,b in boundary:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    unseen=set(neighbors);loops=[]
    while unseen:
        first=min(unseen);loop=[first];prev=None;current=first
        while True:
            choices=[v for v in neighbors[current] if v!=prev]
            if not choices:break
            nxt=choices[0]
            if nxt==first:break
            if nxt in loop:break
            loop.append(nxt);prev,current=current,nxt
        unseen.difference_update(loop)
        if len(loop)>=6:loops.append(loop)
    thread=DEST+'/Materials/M_CombatThread';d['materials'].append(thread);d['material_slots'].append('CombatThread');slot=len(d['materials'])-1
    for loop in loops:
        points=p[loop];nn=normals[loop];inside=np.array([np.mean(adj[v],0)-p[v] for v in loop]);inside-=nn*np.einsum('ij,ij->i',inside,nn)[:,None];inside/=np.maximum(np.linalg.norm(inside,axis=1,keepdims=True),1e-12)
        # Body/head boundary is a native shoulder opening, covered by the
        # separately fitted neck yoke below. Do not sew a second neck there.
        if d.get('rig') in ['Jason','Kaitlin'] and points[:,2].mean()>120:continue
        for offset in [.32,.62]:
            line=points+inside*offset+nn*.015;lengths=np.linalg.norm(np.roll(line,-1,axis=0)-line,axis=1);cum=np.r_[0,np.cumsum(lengths)];length=cum[-1]
            if length<2:continue
            samples=max(3,int(length/.32));pitch=length/samples
            for j in range(samples):
                value=(j+.5)*pitch;idx=min(len(loop)-1,int(np.searchsorted(cum,value)-1));fac=(value-cum[idx])/max(lengths[idx],1e-8);n=unit(nn[idx]*(1-fac)+nn[(idx+1)%len(loop)]*fac);tangent=unit(line[(idx+1)%len(loop)]-line[idx]);cross=unit(np.cross(tangent,n));center=line[idx]*(1-fac)+line[(idx+1)%len(loop)]*fac;start=len(d['positions'])
                ws=d['weights'][loop[idx]]
                for t in [-.10,0,.10]:
                    arch=.020*(1-(t/.10)**2)
                    for k in range(3):
                        theta=2*math.pi*k/3;radial=n*math.cos(theta)+cross*math.sin(theta);d['positions'].append((center+tangent*t+n*arch+radial*.012).tolist());d['weights'].append(copy.deepcopy(ws))
                for section in range(2):
                    for k in range(3):
                        a=start+section*3+k;b=start+section*3+(k+1)%3;c=b+3;e=a+3
                        for f in [[a,c,b],[a,e,c]]:
                            fp=np.array([d['positions'][v] for v in f]);normal=-unit(np.cross(fp[1]-fp[0],fp[2]-fp[0]));d['triangles'].append(f);d['normals'].append([normal.tolist()]*3);d['uv'].append([[0,0],[.03,0],[.03,.01]]);d['triangle_materials'].append(slot)
    return len(loops)
source=(P/'Tools/ModernTacticalSet/shirt_author.py').read_text();tree=ast.parse(source);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='panels')
code=ast.unparse(function).replace('np.dot(normal, nn) < 0','np.dot(normal, nn) > 0').replace('n = unit(np.cross(pp[1] - pp[0], pp[2] - pp[0])).tolist()','n = (-unit(np.cross(pp[1] - pp[0], pp[2] - pp[0]))).tolist()')
ns=dict(np=np,unit=unit,Vector=Vector,BVHTree=BVHTree,math=math,detail=DEST+'/Materials/M_CombatRipstop',thread=DEST+'/Materials/M_CombatThread');exec(compile(code,'combat_sewn_panels','exec'),ns)
def sew(d):
    loops=topstitch(d);ns['panels'](d);d['construction']='Continuous raglan combat cloth, paired inner layer, real crew/cuff/hem topstitch geometry, sewn sleeve pockets and elbow reinforcement';return loops
if __name__=='__main__':
    for rig in ['Jason','Kaitlin']:
        d=read(R/'Authored'/f'shirt_cloth_{rig}.json');loops=sew(d)
        old=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1';config=read(old/'Inputs/modular_outfits.json');config=config if rig=='Jason' else config['body_variants']['kaitlin'];path=config['items']['ue_st6_sleeves']['owner_body_meshes'][rig];row=next(row for row in read(old/'plan.json')['rows'] if row['source']==path);guide=read(old/'Inputs'/row['file']);gp=np.array(guide['positions']);gf=np.array(guide['triangles']);guide=subset(guide,gp[gf,2].mean(1)>120)
        guide['materials']=[DEST+'/Materials/M_CombatStretch'];guide['material_slots']=['CombatNeckYoke'];guide['triangle_materials']=[0]*len(guide['triangles']);pp=np.array(guide['positions']);guide['uv']=[]
        for face,nn in zip(guide['triangles'],guide['normals']):
            axes=[axis for axis in range(3) if axis!=int(np.argmax(np.abs(np.mean(nn,0))))];guide['uv'].append((pp[face][:,axes]/8).tolist())
        merge(d,guide);d['neck_fit_source']=path;write(R/'Authored'/f'shirt_detail_{rig}.json',d);print('TS01_R2_SEWN_DETAIL',rig,loops,len(d['triangles']),flush=True)
