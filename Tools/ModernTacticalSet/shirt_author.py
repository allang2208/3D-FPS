"""Author native sleeves, sewn pocket/elbow panels and matching carrier assemblies."""
import sys,hashlib,copy,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import *
from mathutils import Vector
from mathutils.bvhtree import BVHTree
plan=read(R/'plan.json');rows=[]
fabric=DEST+'/Materials/M_CombatFabric';torso=lambda rig:DEST+'/Materials/MI_CombatTorso_'+rig
detail='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_RangerNylon'
thread='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_StitchThread'
def panels(d):
    bones={b['name']:np.array(b['position']) for b in d['bones']}
    if not all(k in bones for k in ['upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r']):return
    # Trim-only owner assets deliberately carry no sleeve vertices.
    has_sleeve=any('sleeve' in s.lower() or 'ripstop' in s.lower() or 'cuff' in s.lower() for s in d['material_slots'])
    if not has_sleeve:return
    positions=np.array(d['positions']);faces=np.array(d['triangles']);tree=BVHTree.FromPolygons(positions.tolist(),faces.tolist(),all_triangles=True)
    for path,name in [(detail,'CombatPocketAndElbow'),(thread,'CombatSeam')]:
        if path not in d['materials']:d['materials'].append(path);d['material_slots'].append(name)
    mat=d['materials'].index(detail);seam=d['materials'].index(thread)
    def sample(c,radial,offset):
        hit,n,fi,dist=tree.ray_cast(Vector(c+radial*18),Vector(-radial),18)
        if hit is None:raise RuntimeError('Native sleeve panel projection missed')
        a,b,cc=positions[faces[fi]];p=np.array(hit);uv=np.linalg.lstsq(np.column_stack([b-a,cc-a]),p-a,rcond=None)[0];coef=np.clip([1-uv.sum(),uv[0],uv[1]],0,1);coef/=sum(coef)
        weights={}
        for vi,factor in zip(faces[fi],coef):
            for bi,w in d['weights'][vi]:weights[bi]=weights.get(bi,0)+w*factor
        ws=sorted(weights.items(),key=lambda v:-v[1])[:8];total=sum(w for _,w in ws)
        return p+radial*offset,radial,[[bi,w/total] for bi,w in ws]
    def patch(a,b,out,t0,t1,half_angle,offset):
        axis=unit(b-a);out=unit(out-axis*np.dot(out,axis));cross=unit(np.cross(axis,out));nu,nv=10,8;start=len(d['positions']);normals=[]
        us=[0,.007,*np.linspace(.14,.86,7),.993,1];vs=[0,.01,*np.linspace(.18,.82,5),.99,1]
        for iu in range(nu+1):
            t=t0+(t1-t0)*us[iu];c=a+(b-a)*t
            for iv in range(nv+1):
                angle=half_angle*(vs[iv]*2-1);rad=out*math.cos(angle)+cross*math.sin(angle)
                # A low raised hem, softly domed cloth pocket, and closed side facing.
                raised=offset+.07*math.sin(math.pi*iu/nu)*math.sin(math.pi*iv/nv)
                p,n,w=sample(c,rad,raised);d['positions'].append(p.tolist());d['weights'].append(w);normals.append(n.tolist())
        for iu in range(nu):
            for iv in range(nv):
                a0=iu*(nv+1)+iv;v=[a0,a0+nv+1,a0+nv+2,a0+1]
                for f in [(v[0],v[1],v[2]),(v[0],v[2],v[3])]:
                    ff=[start+x for x in f];pp=np.array([d['positions'][x] for x in ff]);normal=unit(np.cross(pp[1]-pp[0],pp[2]-pp[0]));nn=np.mean([normals[x] for x in f],0)
                    if np.dot(normal,nn)<0:ff.reverse();f=tuple(reversed(f))
                    d['triangles'].append(ff);d['triangle_materials'].append(seam if (iu in [0,nu-1] or iv in [0,nv-1]) else mat);d['normals'].append([normals[x] for x in f]);d['uv'].append([[((x%(nv+1))/nv)*.4,((x//(nv+1))/nu)*.7] for x in f])
        boundary=list(range(nv+1))+[i*(nv+1)+nv for i in range(1,nu+1)]+[nu*(nv+1)+i for i in range(nv-1,-1,-1)]+[i*(nv+1) for i in range(nu-1,0,-1)]
        inner=[]
        for x in boundary:
            idx=len(d['positions']);p=np.array(d['positions'][start+x])-np.array(normals[x])*(offset-.035);d['positions'].append(p.tolist());d['weights'].append(d['weights'][start+x]);inner.append(idx)
        for j,x in enumerate(boundary):
            k=(j+1)%len(boundary);f=[start+x,start+boundary[k],inner[k],inner[j]]
            for ff in [f[:3],[f[0],f[2],f[3]]]:
                pp=np.array([d['positions'][x] for x in ff]);n=unit(np.cross(pp[1]-pp[0],pp[2]-pp[0])).tolist();d['triangles'].append(ff);d['normals'].append([n,n,n]);d['uv'].append([[0,0],[.1,0],[.1,.03]]);d['triangle_materials'].append(mat)
    for side,other in [('l','r'),('r','l')]:
        a,b,c=[bones[k+'_'+side] for k in ['upperarm','lowerarm','hand']];out=a-bones['upperarm_'+other]
        for args in [(a,b,out,.23,.64,.65,.16),(a,b,out,.23,.31,.64,.29),(b,c,out,.025,.31,.73,.11)]:
            lengths={k:len(d[k]) for k in ['positions','weights','triangles','triangle_materials','normals','uv']}
            try:patch(*args)
            except RuntimeError as error:
                if str(error)!='Native sleeve panel projection missed':raise
                # Some native first-person rigs crop the shoulder beyond view.
                # Keep their accepted sleeve instead of inventing an unsupported panel.
                for k,length in lengths.items():del d[k][length:]
                print('CROPPED_NATIVE_PANEL',d['rig'],side,flush=True)
for row in plan['rows']:
    if row.get('role')=='body':continue
    d=read(R/'Inputs'/row['file']);rig=row['rig'];materials=[]
    for slot in d['material_slots']:
        materials.append(torso(rig) if 'NeckAndHem' in slot else fabric)
    d['materials']=materials;panels(d)
    if rig in ['Jason','Kaitlin']:
        vest=read(S/'Integration/Delivery'/f'vest_{rig}_Wear.json')
        vest['materials']=[s[7:] if s.startswith('NATIVE:') else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+s.removeprefix('TS01_') for s in vest['material_slots']]
        standalone=copy.deepcopy(d)
        merge(d,vest)
        if row['source'] in [read(R/'Inputs/modular_outfits.json')['items']['ue_st6_sleeves']['rig_meshes'].get('Jason'),read(R/'Inputs/modular_outfits.json')['body_variants']['kaitlin']['items']['ue_st6_sleeves']['rig_meshes'].get('Kaitlin')]:
            body=read(R/'Inputs'/f'Body_{rig}.json');body=subset(body,[m in [0,1,3,8,9] for m in body['triangle_materials']]);body['materials']=[fabric,torso(rig)];body['material_slots']=['CombatNativeShoulder','CombatKnitTorso'];body['triangle_materials']=[0 if m in [0,1] else 1 for m in body['triangle_materials']]
            standalone['body_display_sections']=[0,1,3,8,9];d['body_display_sections']=[0,1,3,8,9]
            merge(standalone,body);write(R/'Authored'/f'shirt_standalone_{rig}.json',standalone)
            display=copy.deepcopy(d);merge(display,body);write(R/'Authored'/f'outfit_display_{rig}.json',display)
    d['contract']='Native sleeve/cuff and current per-pants tucked trim; anatomical rest skeleton; sewn low-profile arm pockets and elbow facings; native torso uses cloth material, no duplicate torso shell'
    out=R/'Authored'/row['file'];write(out,d);rows.append(dict(source=row['source'],rig=rig,file=str(out),asset=DEST+'/Wear/'+rig+'/SK_Combat_'+rig+'_'+out.stem))
    print('TS01_SHIRT_AUTHORED',len(rows),rig,len(d['triangles']),flush=True)
for rig in ['Jason','Kaitlin']:rows.append(dict(source=None,rig=rig,kind='pants_tactical',file=str(R/'Authored'/f'pants_tactical_{rig}.json'),asset=DEST+'/Wear/'+rig+'/SK_TS01_Pants_ModernBootFit_'+rig))
write(R/'authored.json',dict(completed=True,rows=rows))
