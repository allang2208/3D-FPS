"""Restore the intact gloves and fit a closed under-cuff to each native wrist."""
import copy, hashlib, importlib.util, json, shutil
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from geometry import arm_basis, ray_hits, unit, cuff_normals

O=Path(__file__).parent
R=O.parents[1]
LEGACY=R/'SourceAssets/BenelliM4Super9020261006'
OUT=O/'Authored'; OUT.mkdir(exist_ok=True)
BACKUP=O/'Before'; BACKUP.mkdir(exist_ok=True)
ITEM='ue_hardknuckle_gloves'

def save(path,d): path.write_text(json.dumps(d,separators=(',',':')))

def seam_points(d):
    p=np.array(d['positions']); ids=[]; weld={}
    for v in p:
        key=tuple(np.round(v,4)); ids.append(weld.setdefault(key,len(weld)))
    edges=defaultdict(set)
    for f,m in zip(d['triangles'],d['triangle_materials']):
        for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):
            edges[tuple(sorted((ids[a],ids[b])))].add(m)
    boundary={v for e,ms in edges.items() if 2 in ms and len(ms)>1 for v in e}
    return p[[i for i,j in enumerate(ids) if j in boundary]]

def append_cuff(d,skins,side):
    native=skins[0]
    w,axis,e1,e2=arm_basis(native['bones'],side)
    boundaries=[]
    for skin in skins:
        pp=seam_points(skin)
        t=(pp-w)@axis
        selected=t[(np.linalg.norm(pp-w,axis=1)<12)&(t>-2)&(t<10)]
        if len(selected):boundaries.extend(selected.tolist())
    if not boundaries:raise RuntimeError('No real hand/forearm coverage seam '+d['profile']+' '+side)
    distal=.75
    proximal=max(boundaries)+1.25
    if not distal<proximal<10:raise RuntimeError('Unexpected wrist seam')
    rows=max(9,int(np.ceil((proximal-distal)/.5))+1)
    angles=64
    stations=np.linspace(distal,proximal,rows)
    dirs=[e1*np.cos(a)+e2*np.sin(a) for a in np.linspace(0,2*np.pi,angles,endpoint=False)]
    origins=[w+axis*t for t in stations for _ in dirs]
    directions=dirs*rows
    hits=[ray_hits(s['positions'],s['triangles'],origins,directions) for s in skins]
    glovehits=ray_hits(d['positions'],d['triangles'],origins[:angles],dirs)
    base=len(d['positions']); startfaces=len(d['triangles'])
    rows_w=[]; outer=[]; inner=[]; refs=[]
    variants_delta=[]; distal_overlap=[]
    for i,(origin,direction) in enumerate(zip(origins,directions)):
        candidates=[h[i] for h in hits]
        if any(h is None for h in candidates):raise RuntimeError('Incomplete radial wrist surface '+d['profile']+' '+side)
        radius=max(h[0] for h in candidates)
        variants_delta.append(max(h[0] for h in candidates)-min(h[0] for h in candidates))
        t=stations[i//angles]
        # The final lip returns slightly under visible skin. The rest is a
        # thin textile liner, inside the original padded glove cuff.
        q=np.clip((t-(proximal-1.0))/1.0,0,1);q=q*q*(3-2*q)
        clearance=.18*(1-q)-.06*q
        if i<angles:
            if glovehits[i] is None:raise RuntimeError('Distal liner is not inside the glove')
            clearance=min(clearance,glovehits[i][0]-radius-.12)
            distal_overlap.append(glovehits[i][0]-(radius+clearance))
        outer.append((origin+direction*(radius+clearance)).tolist())
        inner.append((origin+direction*(radius+clearance-.16)).tolist())
        refs.append(direction)
        _,fi,bary=candidates[0]
        weights=defaultdict(float)
        for vi,factor in zip(native['triangles'][fi],bary):
            for bone,weight in native['weights'][vi].items():weights[bone]+=float(factor)*weight
        weights={n:max(0,v) for n,v in weights.items() if v>1e-6}
        total=sum(weights.values());rows_w.append({n:v/total for n,v in weights.items()})
    count=len(outer)
    d['positions'].extend(outer+inner)
    d['weights'].extend(rows_w+copy.deepcopy(rows_w))
    localfaces=[]; localuv=[]
    # Existing material atlas: a clean woven patch of the original wrist panel.
    def uv(col,row):return [.08+.18*col/angles,.595+.105*row/(rows-1)]
    def tri(face,coords,outward):
        p=np.array([d['positions'][base+v] for v in face])
        # Native UE buffers keep clockwise fronts. Match the original source.
        if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),outward)>0:
            face=[face[0],face[2],face[1]];coords=[coords[0],coords[2],coords[1]]
        localfaces.append(face);localuv.append(coords)
    for row in range(rows-1):
        for col in range(angles):
            nxt=(col+1)%angles
            a=row*angles+col;b=row*angles+nxt;c=(row+1)*angles+nxt;z=(row+1)*angles+col
            tex=[uv(col,row),uv(col+1,row),uv(col+1,row+1),uv(col,row+1)]
            ref=unit(dirs[col]+dirs[nxt])
            for offset,normal in ((0,ref),(count,-ref)):
                tri([a+offset,b+offset,c+offset],[tex[0],tex[1],tex[2]],normal)
                tri([a+offset,c+offset,z+offset],[tex[0],tex[2],tex[3]],normal)
    for row,normal in ((0,-axis),(rows-1,axis)):
        for col in range(angles):
            nxt=(col+1)%angles;a=row*angles+col;b=row*angles+nxt
            tri([a,b,b+count],[uv(col,row),uv(col+1,row),uv(col+1,row)],normal)
            tri([a,b+count,a+count],[uv(col,row),uv(col+1,row),uv(col,row)],normal)
    # Keep original glove normals and UVs byte-for-byte. Only the new liner
    # receives normals; corners retain a physical, 1.6 mm returned edge.
    points=np.array(outer+inner); faces=np.array(localfaces)
    d['triangles'].extend((faces+base).tolist())
    d['uv'].extend(localuv)
    d['normals'].extend(cuff_normals(points,faces,(rows-1)*angles*4))
    d['triangle_materials'].extend([0]*len(faces))
    edges=Counter(tuple(sorted((int(f[k]),int(f[(k+1)%3])))) for f in faces for k in range(3))
    if set(edges.values())!={2}:raise RuntimeError('Cuff shell has an open edge')
    return dict(side=side,rows=rows,segments=angles,triangles=len(faces),vertices=2*count,
                coverage_seam_min_cm=min(boundaries),coverage_seam_max_cm=max(boundaries),
                proximal_t_cm=proximal,distal_t_cm=distal,
                minimum_distal_overlap_cm=min(distal_overlap),
                max_shared_profile_skin_difference_cm=max(variants_delta),
                closed_shell=True,face_start=startfaces)

def main():
    inventory=json.loads((O/'inventory.json').read_text())
    original_script=LEGACY/'fix_glove_cuff.py'
    if not (BACKUP/'fix_glove_cuff.py').exists():shutil.copy2(original_script,BACKUP/'fix_glove_cuff.py')
    # Keep the proven native binding transport, but not its winding rewrite.
    spec=importlib.util.spec_from_file_location('native_glove_transport',O/'native_transport.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.Y=OUT
    original=json.loads((LEGACY/'EquipmentAuthored/M4_ue_hardknuckle_gloves.precuff.json').read_text())
    save(OUT/('M4_'+ITEM+'.json'),original)
    module.derive(original)
    groups=defaultdict(list)
    for row in inventory:
        if row['file'] not in groups[row['profile']]:groups[row['profile']].append(row['file'])
    report=[]
    for profile,files in groups.items():
        path=OUT/(profile+'_'+ITEM+'.json')
        previous=LEGACY/'EquipmentAuthored'/path.name
        if not (BACKUP/path.name).exists():shutil.copy2(previous,BACKUP/path.name)
        d=json.loads(path.read_text());skins=[json.loads(Path(f).read_text()) for f in files]
        base_faces=len(d['triangles']);base_vertices=len(d['positions'])
        source_hash=hashlib.sha256(json.dumps(d,separators=(',',':')).encode()).hexdigest()
        sides=(profile[-1],) if profile.endswith(('_l','_r')) else ('l','r')
        cuffs=[append_cuff(d,skins,s) for s in sides]
        d['hardknuckle_repair']=dict(version='20261017',base_faces=base_faces,base_vertices=base_vertices,
                                    original_sha256=source_hash,cuffs=cuffs)
        save(path,d)
        report.append(dict(profile=profile,file=str(path),skin_sources=[s['source'] for s in skins],
                           asset=next(x['glove'] for x in inventory if x['profile']==profile),
                           previous_source_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
                           vertices=len(d['positions']),triangles=len(d['triangles']),cuffs=cuffs))
        print('CUFF_AUTHORED',profile,len(d['triangles']),flush=True)
    (O/'author_receipt.json').write_text(json.dumps(report,indent=2))
    print('HARDKNUCKLE_AUTHORED',len(report),flush=True)

if __name__=='__main__':main()
