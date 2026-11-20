"""Tailor the patrol shirt on both current shoulder fits and their native waists."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from patrol_shirt_world_pattern import SLOTS,Cut,Skin,sleeve,smooth,unit

P=Path(__file__).resolve().parents[2]
SET=P/'SourceAssets/ModernTacticalSet20261113'
ROOT=SET/'PatrolShirtR2'
WORLD=ROOT/'World'
R4=SET/'CombatShirtR4'
SHOULDER=SET/'ShoulderFit20261118'
GAME='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/PatrolShirtR2'
MAT=GAME+'/Materials/M_'
ITEM='ue_modern_kevlar_vest'
BODY_NAMES=('Jason','Kaitlin')

def read(path):
    return json.loads(Path(path).read_bytes())

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.writing')
    with tmp.open('w',encoding='utf8') as stream:json.dump(obj,stream,separators=(',',':'),allow_nan=False)
    tmp.replace(path)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def corrected(points,rig,section):
    source=np.load(SHOULDER/f'{rig}-{section}.npz')
    p=np.asarray(points,float).copy();dist,ix=cKDTree(source['before']).query(p)
    hit=dist<.00008;p[hit]=source['after'][ix[hit]]
    return p

def normal_field(p,f):
    face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    out=np.zeros_like(p)
    for j in range(3):np.add.at(out,f[:,j],face)
    return unit(out)

def append_direct(d,key,points,normals,weights,tri,uv,mat):
    p=np.asarray(points);nn=np.asarray(normals);f=np.asarray(tri).copy()
    face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    flip=np.sum(face*nn[f].mean(1),axis=1)<0;f[flip]=f[flip,::-1]
    valid=np.linalg.norm(face,axis=1)>1.e-7;f=f[valid];offset=len(d['positions']);start=len(d['triangles'])
    d['positions']+=p.round(6).tolist();d['weights']+=weights;d['triangles']+=(f+offset).tolist()
    d['normals']+=nn[f].round(6).tolist();d['uv']+=np.asarray(uv)[f].round(6).tolist();d['triangle_materials'] += [SLOTS.index(mat)]*len(f)
    d['parts'][key]=[start,len(d['triangles'])]

def collar(d,skin,rim):
    # The TS01 shirt has a low neckline under its carrier. Turn a narrow
    # binding over the actual fitted rim, using the same weights as the cloth.
    p=np.array(d['positions'])[rim];center=skin.bones['neck_01'];theta=np.arctan2(p[:,0]-center[0],p[:,1]-center[1])%(2*np.pi)
    rr=np.argsort(theta);p=p[rr];theta=theta[rr];rim=np.asarray(rim)[rr]
    keep=(theta>.055)&(theta<2*np.pi-.055);p=p[keep];theta=theta[keep];rim=rim[keep]
    rad=unit(np.column_stack((p[:,:2]-center[:2],np.zeros(len(p)))))
    front=(1+np.cos(theta))*.5;top=.78-.21*front**3
    rows=[(-.075,.07),(.27,.13),(.72,.12),(.978,.025),(1.,-.10),(.966,-.255),(.29,-.20),(-.055,-.12)]
    pp=[];nn=[];uv=[];ww=[];faces=[]
    path=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    for j,(rise,thick) in enumerate(rows):
        pts=p+rad*(thick+rise*.09) + np.column_stack((np.zeros((len(p),2)),top*rise))
        pp.extend(pts);n=rad.copy() if j<4 else -rad.copy()
        if j in (3,4):n=unit(n*.24+[0,0,1])
        nn.extend(n);uv.extend(np.column_stack((path,top*rise))/8);ww.extend([d['weights'][i] for i in rim])
        if j:
            ix=np.arange(len(p)-1)+(j-1)*len(p);iy=ix+len(p)
            faces.extend(np.column_stack((ix,ix+1,iy+1)));faces.extend(np.column_stack((ix,iy+1,iy)))
    append_direct(d,'bound_low_neckline',pp,nn,ww,faces,uv,'PS_Binding')
    # The soft front zip starts below the throat and follows the torso surface.
    ztop=p[:,2].min();half=.54;z=np.linspace(ztop-14.5,ztop+.02,45)
    def front_chart(q):
        starts=np.column_stack((q[:,0]+center[0],np.full(len(q),center[1]),q[:,1]))
        return skin.hit(starts,np.tile([0.,1.,0.],(len(q),1)),10.)
    from patrol_shirt_world_pattern import polygon
    cut=Cut(d,skin)
    tape=polygon([(-.73,z[0]+.41),(0,z[0]),(.73,z[0]+.41),(.72,z[-1]),(-.72,z[-1])],.11)
    cut.panel('front_zip_welt',front_chart,tape,'PS_Ripstop',.16,.20)
    for side in [-1,1]:
        cut.line('front_welt_stitch'+str(side),front_chart,[(side*half,z[0]+.75),(side*half,z[-1]-.1)],.027,.17,'PS_Thread',.38)
    cut.line('front_zip_coil',front_chart,[(0,z[0]+.56),(0,z[-1]-.15)],.10,.185,'PS_Hardware',.255)
    pull=polygon([(-.27,z[-1]-.47),(.26,z[-1]-.42),(.32,z[-1]-1.73),(.06,z[-1]-2.2),(-.25,z[-1]-1.9)],.10)
    cut.panel('zip_pull',front_chart,pull,'PS_Hardware',.32,.085)

def seams(d,skin,count):
    p=skin.p;f=skin.f;materials=np.asarray(d['triangle_materials'][:count])
    by_edge={}
    for tri,mat in zip(f,materials):
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            key=(min(a,b),max(a,b));by_edge[key]=by_edge.get(key,0)|(1<<int(mat))
    n=normal_field(p,f);edges=[e for e,v in by_edge.items() if v & 1 and v & 2]
    hem=[e for e in by_edge if 92<max(p[list(e),2])<96 and np.max(np.abs(p[list(e),0]))<20]
    # Only open bottom boundaries carry the coverstitch at the hem.
    ed=np.sort(np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1)
    unique,counts=np.unique(ed,axis=0,return_counts=True)
    hem=[e for e in unique[counts==1] if p[e,2].max()<103 and np.max(np.abs(p[e,0]))<20]
    for label,selection,width,offsets in [('raglan_topstitch',edges,.034,[-.135,.135]),('hem_coverstitch',hem,.032,[.22,.43])]:
        pp=[];norm=[];ww=[];uv=[];faces=[]
        for a,b in selection:
            line=p[b]-p[a];length=np.linalg.norm(line)
            if length<.1 or length>7:continue
            axis=line/length;side=unit(np.cross(axis,n[a]+n[b]))
            if label=='hem_coverstitch' and side[2]<0:side*=-1
            for j in range(max(1,round(length/.44))):
                t=(j+.5)/max(1,round(length/.44));ctr=p[a]*(1-t)+p[b]*t;nn=unit(n[a]*(1-t)+n[b]*t);extent=min(.143,length*.35)
                weight={}
                for ix,m in ((a,1-t),(b,t)):
                    for bi,bw in d['weights'][ix]:weight[bi]=weight.get(bi,0)+bw*m
                ws=[[i,w] for i,w in weight.items()]
                for offset in offsets:
                    c=ctr+side*offset+nn*.054;v=len(pp)
                    pp.extend([c-axis*extent,c+side*width,c+axis*extent,c-side*width,c+nn*.028])
                    norm.extend([nn]*5);ww.extend([ws]*5);uv.extend([[0,.5],[.5,1],[1,.5],[.5,0],[.5,.5]])
                    faces.extend([[v,v+1,v+4],[v+1,v+2,v+4],[v+2,v+3,v+4],[v+3,v,v+4]])
        if pp:append_direct(d,label,pp,norm,ww,faces,np.array(uv)*.025,'PS_Thread')

def master(rig):
    raw=read(R4/'Authored'/f'shirt_detail_{rig}.json')
    outer=read(R4/'Authored'/f'shirt_outer_{rig}.json')
    count=len(outer['triangles']);verts=2*len(outer['positions']);del outer
    ids=np.asarray(raw['triangle_materials']);stop=int(np.flatnonzero(ids==4)[0])
    f=np.array(raw['triangles'][:stop]);p=corrected(raw['positions'][:verts],rig,'cloth')
    n=normal_field(p,f[:count]);nn=np.array(raw['normals'][:stop])
    nn[:count]=n[f[:count]];nn[count:2*count]=-n[f[count:2*count]-verts//2]
    d={key:raw[key] for key in ['rig','source','bones']}
    d.update(positions=p.round(6).tolist(),triangles=f.tolist(),weights=raw['weights'][:verts],normals=nn.round(6).tolist(),
             uv=raw['uv'][:stop],triangle_materials=np.array([1,0,4,0])[ids[:stop]].tolist(),material_slots=SLOTS[:],materials=[MAT+n for n in SLOTS],
             parts={'continuous_raglan_shell':[0,count],'inner_shell_and_cuff_turn':[count,stop]})
    skin=Skin(d,count);seams(d,skin,count);collar(d,skin,raw['r4_pattern']['neck_vertices'])
    for flank in ('l','r'):sleeve(Cut(d,skin),flank)
    d['construction']='Native shoulder, cuff and collar fit. Low bound neckline, soft reverse-coil placket, raglan knit body, angled sleeve pockets, articulated elbow darts and folded cuff tabs.'
    write(WORLD/f'shirt_{rig}.json',d)
    print('PATROL_WOVEN',rig,len(d['triangles']),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rigs',nargs='*',default=BODY_NAMES)
    for name in parser.parse_args().rigs:master(name)
