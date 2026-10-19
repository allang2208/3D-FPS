"""Retain each fitted native glove; author mage surfaces and seated wrist ornaments."""
import sys,json,math,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageGloves20261019'
sys.path.insert(0,str(P/'Tools/ModularOutfit'));sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import black_leather_tailored_surface as lib
import geometry as geo

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')

master=read(R/'Sources/M4.json');anatomy=read(lib.ANATOMY)['anatomy'];rows=[]
def canonical(d):
    # Jason also weights finger corrective joints. Their named ancestor defines
    # the corresponding M4 author frame; the original weights remain untouched.
    bones=d['bones'];byid={v['index']:k for k,v in bones.items()}
    transforms={k:lib.matrix(v)@np.linalg.inv(lib.matrix(master['bones'][k])) for k,v in bones.items() if k in master['bones']}
    for key in {k for w in d['weights'] for k in w}:
        ancestor=key
        while ancestor not in transforms:ancestor=byid[bones[ancestor]['parent']]
        transforms[key]=transforms[ancestor]
    p=np.asarray(d['positions']);n=lib.vertex_normals(d);blend=np.array([sum(transforms[k]*v for k,v in w.items()) for w in d['weights']]);inverse=np.linalg.inv(blend)
    cp=np.einsum('nij,nj->ni',inverse,np.c_[p,np.ones(len(p))])[:,:3];cn=lib.unit(np.einsum('nji,nj->ni',blend[:,:3,:3],n))
    return cp,cn,blend[:,:3,:3]

for row in read(R/'inputs.json')['rows']:
    name=row['profile'];d=read(Path(row['file']));p,n,delta=canonical(d)
    fields=lib.design_fields(p,n,d['weights'],master['bones'],anatomy)
    f=np.c_[fields['design'],fields['back'],fields['hand'],fields['digit'],fields['digit_t'],fields['finger_arc'],fields['finger_seam']]
    group='Body' if name in ('Body','Jason') else 'M4'
    # The mage sleeve's fitted inner cuff has less clearance than a tactical
    # sleeve. Taper only the overlapped glove wrist by 1.2 mm; keep the grip.
    shift=np.zeros_like(p)
    for side in ('l','r'):
        ids=np.array([i for i,w in enumerate(d['weights']) if sum(v for k,v in w.items() if k.endswith('_'+side))>.5],dtype=int)
        if not len(ids):continue
        frame,wrist=lib.frame(master['bones'],anatomy,side);radial=p[ids]-wrist;radial-=np.outer(radial@frame[1],frame[1])
        shift[ids]=-lib.unit(radial)*(.12*(1-lib.smooth(-.9,.5,fields['design'][ids,1])))[:,None]
    fitted=np.asarray(d['positions'])+np.einsum('nij,nj->ni',delta,shift)
    d['normals']=lib.transported_normals(d,fitted).tolist();d['positions']=fitted.tolist();p+=shift
    d.update(profile=name,binding_source=d['source'],material_slots=['MageClothLeather','MageSilver','MageSapphire'],contract='Native fitted full-finger glove envelope, rolled cuff and weights retained; mage textile and embroidery; small dorsal wrist ornament; no animation edits')
    if name in ('Body','M4'):
        (R/'Fields').mkdir(exist_ok=True);np.savez_compressed(R/'Fields'/(name+'.npz'),fields=f.astype('float32'),canonical=p.astype('float32'),normals=n.astype('float32'))
    original_count=len(d['triangles']);orn=dict(positions=[],triangles=[],weights=[],uv=[],normals=[],triangle_materials=[])
    for side in ('l','r'):
        ids=np.array([i for i,w in enumerate(d['weights']) if sum(v for k,v in w.items() if k.endswith('_'+side))>.5 and fields['back'][i]>.75 and fields['hand'][i]>.75],dtype=int)
        if not len(ids):continue
        # The ornament stays within the dorsal wrist tab, behind the bend crease.
        distance=np.linalg.norm(fields['design'][ids]-[-.55,-.20],axis=1);nearest=ids[np.argmin(distance)]
        frame,_=lib.frame(master['bones'],anatomy,side);x,y,z=frame
        cp=p[nearest]+z*.025;transform=delta[nearest];origin=np.array(d['positions'][nearest]);w=d['weights'][nearest]
        def native(q):return origin+transform@(q-p[nearest])
        ring=[native(cp+x*.59*math.sin(a)+y*.66*math.cos(a)) for a in np.linspace(0,math.tau,48,endpoint=False)]
        geo.tube(orn,ring,.052,1,w,closed=True,sides=6)
        rings=[]
        for t in np.linspace(0,.94,8):
            rr=math.sqrt(1-t*t);rings.append([geo.vertex(orn,native(cp+x*.48*rr*math.sin(a)+y*.55*rr*math.cos(a)+z*(.02+.17*t)),w) for a in np.linspace(0,math.tau,48,endpoint=False)])
        for j in range(len(rings)-1):
            for i in range(48):
                q=[rings[j][i],rings[j][(i+1)%48],rings[j+1][(i+1)%48],rings[j+1][i]]
                for tri in ((0,1,2),(0,2,3)):geo.face(orn,[q[k] for k in tri],2,[[0,0],[1,0],[1,1]],transform@z)
        tip=geo.vertex(orn,native(cp+z*.19),w)
        for i in range(48):geo.face(orn,[rings[-1][i],rings[-1][(i+1)%48],tip],2,[[0,0],[1,0],[.5,1]],transform@z)
    geo.finish(orn);offset=len(d['positions'])
    d['positions']+=orn['positions'];d['weights']+=orn['weights'];d['triangles'] += [[i+offset for i in tri] for tri in orn['triangles']]
    for key in ('normals','uv','triangle_materials'):d[key]+=orn[key]
    output=R/'Authored'/(name+'.json');write(output,d)
    rows.append(dict(profile=name,source=row['source'],authored=str(output),group=group,source_triangles=original_count,triangles=len(d['triangles']),aliases=row['aliases']))
    print('MAGE_GLOVE_AUTHORED',name,len(d['triangles']),flush=True)
write(R/'manifest.json',dict(rows=rows,new_animations=0,runtime_tested=False,geometry_reference='ue_field_gloves_black',concept='Design/blue-mage-gloves-concept-v01.png'))
