"""Brown palm/back shells with five root openings, native V7 bindings, metric UVs.

No base skin, black gloves or animation assets are modified. Run with local Python.
"""
import json, hashlib
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

P=Path(__file__).resolve().parents[2]
ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
BARE=P/'SourceAssets/ModularOutfit20260925/BarePalmV7'
SOURCES=P/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def smooth(a,b,v):
    x=np.clip((v-a)/(b-a),0,1);return x*x*(3-2*x)
def bind(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
def normals(p,t):
    c=p[t];f=-unit(np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0]));n=np.zeros_like(p)
    for k in range(3):
        a=unit(c[:,(k+1)%3]-c[:,k]);b=unit(c[:,(k+2)%3]-c[:,k])
        np.add.at(n,t[:,k],f*np.arccos(np.clip((a*b).sum(1),-1,1))[:,None])
    return unit(n)
canonical=read(BARE/'M4_original.json')
anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
config=read(P/'Content/ColdSteelData/modular_outfits.json')

def shell(base,bones,frames,root_weight=.40,openings_per_hand=3):
    """Clip skin triangles at finger-root blend fields; close outer/inner shell rims."""
    p=np.asarray(base['positions']);t=np.asarray(base['triangles']);w=base['weights']
    faces=t[np.asarray(base['triangle_materials'])==2]
    field=np.full(len(p),-1.)
    for vi in np.unique(faces):
        # Thumb 01 is the metacarpal inside the palm; its exposed digit starts at 02.
        digit=max(sum(value for name,value in w[vi].items()
                      if any(name==f'{finger}_{seg:02d}_{side}'
                             for side in ('l','r') for seg in ((2,3) if finger=='thumb' else (1,2,3))))
                  for finger in ('index','middle','ring','pinky','thumb'))
        field[vi]=digit-root_weight
    refs=[];cp=[];cw=[];lookup={};tri=[]
    def vertex(ref):
        key=tuple((int(i),round(float(v),10)) for i,v in sorted(ref.items()) if v>1e-10)
        if key not in lookup:
            lookup[key]=len(refs);refs.append(dict(key))
            cp.append(sum(p[i]*v for i,v in key));weights=defaultdict(float)
            for i,v in key:
                for bn,bw in w[i].items():weights[bn]+=v*bw
            cw.append(dict(weights))
        return lookup[key]
    for face in faces:
        poly=[]
        for j in range(3):
            a=int(face[j]);b=int(face[(j+1)%3]);fa=field[a];fb=field[b]
            if fa<=0:poly.append({a:1.})
            if (fa<0<fb) or (fb<0<fa):
                alpha=float(fa/(fa-fb));poly.append({a:1-alpha,b:alpha})
        if len(poly)>=3:
            ids=[vertex(x) for x in poly]
            for k in range(1,len(ids)-1):tri.append([ids[0],ids[k],ids[k+1]])
    cp=np.asarray(cp);tri=np.asarray(tri)
    # Cut borders must retain the complete skin's normals. Normals recomputed
    # from only the surviving patch lean into the neighbouring thumb web.
    source_normals=normals(p,faces)
    n=unit(np.asarray([sum(source_normals[i]*a for i,a in ref.items()) for ref in refs]))
    edge_faces=defaultdict(list)
    for f in tri:
        for k in range(3):edge_faces[tuple(sorted((int(f[k]),int(f[(k+1)%3]))))].append((int(f[k]),int(f[(k+1)%3])))
    borders=[v[0] for v in edge_faces.values() if len(v)==1]
    if any(len(v)>2 for v in edge_faces.values()):raise RuntimeError('Non-manifold source hand')
    adj=defaultdict(list)
    for a,b in borders:adj[a].append(b);adj[b].append(a)
    if any(len(v)!=2 for v in adj.values()):raise RuntimeError('Opening is not a closed contour')
    loops=[];remaining=set(adj)
    while remaining:
        start=min(remaining);prev=-1;v=start;loop=[]
        while v not in loop:
            loop.append(v);remaining.discard(v);nn=adj[v];nxt=nn[0] if nn[0]!=prev else nn[1];prev,v=v,nxt
        loops.append(loop)
    # Extending coverage over the webs can split the shared knuckle opening
    # into separate finger ports; all resulting contours are closed above.
    sides={('l' if sum(v for k,v in x.items() if k.endswith('_l'))>.5 else 'r') for x in cw}
    if openings_per_hand is not None and len(loops)!=openings_per_hand*len(sides):raise RuntimeError(f'Unexpected glove openings: {len(loops)} for {sides}')
    edge=np.asarray(list(edge_faces));length=np.linalg.norm(cp[edge[:,0]]-cp[edge[:,1]],axis=1)
    graph=coo_matrix((np.r_[length,length],(np.r_[edge[:,0],edge[:,1]],np.r_[edge[:,1],edge[:,0]])),shape=(len(cp),len(cp))).tocsr()
    boundary=np.asarray(sorted(adj));distance=dijkstra(graph,indices=boundary,min_only=True,directed=False)
    arc=np.zeros(len(cp));loop_lengths=[]
    for loop in loops:
        s=0.
        for j,v in enumerate(loop):arc[v]=s;s+=float(np.linalg.norm(cp[v]-cp[loop[(j+1)%len(loop)]]))
        loop_lengths.append(s)
    _,near=cKDTree(cp[boundary]).query(cp);arc=arc[boundary[near]]
    local=np.zeros_like(cp);back=np.zeros(len(cp))
    for vi,x in enumerate(cw):
        side='l' if sum(v for k,v in x.items() if k.endswith('_l'))>.5 else 'r'
        f=frames[side];basis=np.asarray([f['across'],f['forward'],f['dorsal']]);local[vi]=basis@(cp[vi]-f['wrist'])
        back[vi]=smooth(-.10,.6,float(n[vi]@np.asarray(f['dorsal'])))
    # Retain the skin; the leather is a thin shell, with volume on the back only.
    outer=.035+.045*back
    outer+=.08*np.exp(-((distance-.13)/.10)**2)
    # Feather into the exact shared skin edge. The seam's positions and weights
    # are shared with the exposed-skin companion, including in animated poses.
    taper=smooth(0,.20,distance)
    outer*=taper
    inner=.012*taper
    offsets=np.r_[n*outer[:,None],n*inner[:,None]]
    q=np.r_[cp,cp]+offsets;count=len(cp)
    all_tri=tri.tolist()+[[int(a+count),int(c+count),int(b+count)] for a,b,c in tri]
    for a,b in borders:all_tri.extend([[b,a,a+count],[b,a+count,b+count]])
    all_tri=np.asarray(all_tri);vn=normals(q,all_tri)
    # Each UV chart is a metric projection of the canonical hand, and is the
    # actual tangent UV channel. Normal maps therefore use the same chart basis.
    uv=[];uv1=[];uv2=[]
    fields=np.c_[1-back,distance];details=np.c_[arc,np.zeros(count)]
    for fi,face in enumerate(all_tri):
        ids=face%count;points=local[ids];cross=np.cross(points[1]-points[0],points[2]-points[0]);axis=int(np.argmax(abs(cross)))
        keep=[a for a in range(3) if a!=axis]
        coords=points[:,keep]/25.
        if cross[axis]<0:coords[:,0]*=-1
        coords+=np.asarray([axis*.173,axis*.293])
        if fi>=2*len(tri):
            coords=np.c_[arc[ids]/25.,np.where(face<count,outer[ids],inner[ids])/25.]
        uv.append(coords.tolist());uv1.append(fields[ids].tolist())
        d=details[ids].copy();d[:,1]=(face>=count).astype(float)
        uv2.append(d.tolist())
    # Weld the collapsed outer/lining seam, omitting the zero-area rim faces.
    merge=np.arange(len(q));merge[boundary+count]=boundary
    welded=merge[all_tri];valid=np.array([len(set(f))==3 for f in welded])
    corner_normals=np.where((all_tri<count)[:,:,None],n[all_tri%count],-n[all_tri%count])
    return dict(refs=refs+refs,positions=q,weights=cw+cw,triangles=welded[valid],offsets=offsets,
                normals=corner_normals[valid],uv=np.asarray(uv)[valid].tolist(),uv1=np.asarray(uv1)[valid].tolist(),uv2=np.asarray(uv2)[valid].tolist(),loops=len(loops),loop_cm=loop_lengths)

def save_profile(name,base,native,shape,source_mapping=None,canonical_bones=None):
    mapping=source_mapping or {i:i for i in range(len(base['positions']))}
    mats={bn:(bind(native['bones'][bn])@np.linalg.inv(bind(canonical_bones[bn])))[:3,:3]
          for bn in native['bones'] if bn in canonical_bones} if canonical_bones else None
    positions=[];weights=[];valid=[];norm_maps={}
    p=np.asarray(base['positions'])
    native_normals=normals(p,np.asarray(base['triangles']))
    for i,ref in enumerate(shape['refs']):
        if not all(v in mapping for v in ref):continue
        ww=defaultdict(float)
        for v,a in ref.items():
            for bn,bw in base['weights'][mapping[v]].items():ww[bn]+=a*bw
        total=sum(ww.values());ww={bn:v/total for bn,v in ww.items() if v>1e-8}
        m=sum(mats[bn]*value for bn,value in ww.items()) if mats else np.eye(3)
        native_normal=unit(sum(native_normals[mapping[v]]*a for v,a in ref.items()))
        positions.append((sum(p[mapping[v]]*a for v,a in ref.items())+native_normal*np.linalg.norm(shape['offsets'][i])).tolist())
        weights.append(ww);valid.append(i);norm_maps[i]=np.linalg.inv(m).T
    remap={v:i for i,v in enumerate(valid)}
    faces=[i for i,f in enumerate(shape['triangles']) if all(int(v) in remap for v in f)]
    profile=next(v for v in config['profiles'].values() if v['rig_profile']==name)
    native_source=profile.get('original_gloved_source',profile['native_bare_skin'])
    data=dict(profile=name,source=base['source'],binding_source=native_source,base_mesh=profile['native_bare_skin'],
              positions=positions,weights=weights,triangles=[[remap[int(v)] for v in shape['triangles'][i]] for i in faces],
              normals=[[unit(norm_maps[int(v)]@shape['normals'][i][j]).tolist() for j,v in enumerate(shape['triangles'][i])] for i in faces],
              uv=[shape['uv'][i] for i in faces],uv1=[shape['uv1'][i] for i in faces],uv2=[shape['uv2'][i] for i in faces],
              triangle_materials=[0]*len(faces),family='FingerlessHuntV2',surface_winding='ue_native',
              contract='Five fully exposed digits; palm/back short leather shell; retain native skin; no new animations',
              bones=native['bones'])
    # Current native rest poses may already bend metacarpals. Recompute on the
    # fitted surface instead of transforming a canonical patch normal through
    # a blended inverse bind, which can aim an opening into the skin.
    data['normals']=normals(np.asarray(positions),np.asarray(data['triangles']))[np.asarray(data['triangles'])].tolist()
    path=OUT/f'{name}.json';path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('FINGERLESS_AUTHORED',name,len(positions),len(faces),flush=True)
    return dict(profile=name,authored=str(path),vertices=len(positions),triangles=len(faces),sha256=hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__':
    frames={s:{k:np.asarray(v) for k,v in f.items() if k in ('wrist','across','forward','dorsal')} for s,f in anatomy.items()}
    shape=shell(canonical,canonical['bones'],frames)
    manifest=[];cp=np.asarray(canonical['positions']);tree=cKDTree(cp)
    for entry in read(BARE/'manifest.json'):
        name=entry['profile'];base=read(Path(entry['authored']));native=read(SOURCES/f'{name}.json')
        rest=np.asarray(base['canonical_positions'])
        idx=np.arange(len(cp)) if len(rest)==len(cp) else np.flatnonzero(cp[:,0]*(-1 if rest[:,0].mean()<0 else 1)>0)
        if len(idx)!=len(rest) or np.max(np.linalg.norm(cp[idx]-rest,axis=1))>1e-6:
            dist,idx=tree.query(rest)
            if dist.max()>1e-6 or len(set(idx))!=len(idx):raise RuntimeError('Canonical correspondence changed '+name)
        mapping={int(c):i for i,c in enumerate(idx)}
        manifest.append(save_profile(name,base,native,shape,mapping,canonical['bones']))
    # The world body uses its own skin and skeleton; derive its openings locally.
    body=read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_skin.json')
    native=read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_source.json')
    base=dict(source=body['source'],positions=body['vertices'],weights=body['weights'],triangles=body['triangles'],triangle_materials=body['materials'])
    bf={}
    for side,f in frames.items():
        bn='hand_'+side;r=(bind(native['bones'][bn])@np.linalg.inv(bind(canonical['bones'][bn])))[:3,:3]
        bf[side]={k:unit(r@f[k]) for k in ('across','forward','dorsal')};bf[side]['wrist']=np.asarray(native['bones'][bn]['position'])
    # The source world-body webs join the thumb and knuckle openings into one
    # open palm edge. Keep its native surface instead of forcing V7 topology.
    bs=shell(base,native['bones'],bf,.40,2);manifest.append(save_profile('Body',base,native,bs))
    # Bow's accepted arms use the existing +90-degree Z rebind of M4 hands.
    bow=read(OUT/'M4.json');rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    source,profile=next((k,v) for k,v in config['profiles'].items() if v['rig_profile']=='Bow')
    bow.update(profile='Bow',source=source,binding_source=profile['native_bare_skin'],base_mesh=profile['native_bare_skin'])
    bow['positions']=(np.asarray(bow['positions'])@rotation.T).tolist()
    bow['normals']=(np.asarray(bow['normals'])@rotation.T).tolist()
    for b in bow['bones'].values():
        b['position']=(rotation@np.asarray(b['position'])).tolist();b['axes']=(np.asarray(b['axes'])@rotation.T).tolist()
    path=OUT/'Bow.json';path.write_text(json.dumps(bow,separators=(',',':')))
    manifest.append(dict(profile='Bow',authored=str(path),vertices=len(bow['positions']),triangles=len(bow['triangles']),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'design.json').write_text(json.dumps(dict(exposure='five digits from roots',coverage=[],canonical_openings=shape['loops'],
        loop_circumference_cm=shape['loop_cm'],contact_outer_mm=.35,dorsal_outer_mm=2.60,edge_roll_extra_mm=.8,
        uv_tile_cm=25,skin_retained=True,new_animations=0,runtime_tested=False),indent=2)+'\n')
