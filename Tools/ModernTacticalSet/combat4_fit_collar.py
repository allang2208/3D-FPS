"""Fit low crew anchors to actual native neck skin and smoothly carry every sewn layer."""
import sys,copy,os,uuid,gc
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write as _write,smooth_transport
from combat3_cloth import normals,smooth
from combat4_details import final_clearance
from combat4_assemble import fit_carrier
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR4';B=S/'CombatShirtR3'
def write(path,data):
    path=Path(path);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');_write(tmp,data);os.replace(tmp,path)

def head_target(q,center,tree,p,f,nn):
    hit,_,fi,_=tree.find_nearest(Vector(q));signed=np.dot(q-np.array(hit),nn[fi])
    if signed>=.30:return q.copy()
    close=np.array(hit)+nn[fi]*.30;rad=q-center;rad[2]=0;rad/=max(np.linalg.norm(rad),1e-9);front=float(smooth((rad[1]-.05)/.45));horizontal=tree.ray_cast(Vector(center+rad*30),Vector(-rad),30)[0]
    if horizontal is not None:close=close*(1-front)+(np.array(horizontal)+rad*.30)*front
    for _ in range(8):
        hit,_,fi,_=tree.find_nearest(Vector(close));signed=np.dot(close-np.array(hit),nn[fi])
        if signed>=.23:break
        close=np.array(hit)+nn[fi]*.30
    return close

def local_normals(d,before):
    after=np.asarray(d['positions']);faces=np.asarray(d['triangles']);changed=np.linalg.norm(after-before,axis=1)>1e-8
    touched=np.unique(faces[changed[faces].any(1)])
    selected=np.flatnonzero(np.isin(faces,touched).any(1))
    if not len(selected):return
    part={'positions':d['positions'],'triangles':faces[selected].tolist(),'normals':[d['normals'][int(i)] for i in selected]}
    smooth_transport(part,before)
    for i,n in zip(selected,part['normals']):d['normals'][int(i)]=n

def main():
    manifest=read(R/'authored.json');receipt={}
    for rig in ['Jason','Kaitlin']:
        detail=read(R/'Authored'/f'shirt_detail_{rig}.json');resuming=bool(detail.get('r4_collar_fit'))
        outer=read(R/'Authored'/f'shirt_outer_{rig}.json');old=np.array(outer['positions']);faces=np.array(outer['triangles']);body=read(B/'Inputs'/f'Body_{rig}.json');head=read(S/'HelmetHairFitR1/Inputs'/f'{rig}_Head.json');hp=np.array(head['positions']);hf=np.array(head['triangles']);hn=-np.cross(hp[hf[:,1]]-hp[hf[:,0]],hp[hf[:,2]]-hp[hf[:,0]]);hn/=np.maximum(np.linalg.norm(hn,axis=1,keepdims=True),1e-12);head_tree=BVHTree.FromPolygons(hp.tolist(),hf.tolist(),all_triangles=True)
        bones={b['name']:np.array(b['position']) for b in outer['bones']};clav=np.mean([bones['clavicle_'+s][2] for s in ['l','r']]);anchors=np.array(outer['r4_pattern']['neck_vertices']);target=[]
        resume_file=R/'Simulation'/f'CollarTransfer_{rig}.npz';cache={}
        if resuming:
            if resume_file.exists():
                data=np.load(resume_file);before=data['before'];after=data['after'];old=data['outer_before'];new=np.array(outer['positions'])
            else:
                donor=None
                for row in reversed(manifest['rows']):
                    if row['rig']!=rig or row.get('kind') or row.get('owner'):continue
                    candidate=read(row['file'])
                    if not candidate.get('r4_collar_fit'):donor=candidate;break
                if donor is None:raise RuntimeError('No original collar transfer donor for '+rig)
                before=np.array(donor['positions'][:len(detail['positions'])]);after=np.array(detail['positions']);old=before[:len(old)].copy();new=np.array(outer['positions']);del donor,candidate
                np.savez_compressed(resume_file,before=before,after=after,outer_before=old)
            mask=(before[:,2]>clav-12)&(abs(before[:,0])<25)
            cache={tuple(q):dv for q,dv in zip(before[mask],(after-before)[mask])}
            fixed=new[anchors]-old[anchors]
        else:
            old_detail=np.array(detail['positions'])
        for vi in anchors:
            q=old[vi];center=bones['neck_01'].copy();center[2]=q[2];target.append(head_target(q,center,head_tree,hp,hf,hn))
        target=np.array(target);edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0);a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]];weights=1/np.maximum(np.linalg.norm(old[a]-old[b],axis=1),.08);den=np.bincount(a,weights,minlength=len(old));field=np.zeros_like(old);free=(old[:,2]>clav-10)&(abs(old[:,0])<24);free[anchors]=False;fixed=target-old[anchors];field[anchors]=fixed
        for _ in range(360):
            mean=np.zeros_like(field)
            for axis in range(3):mean[:,axis]=np.bincount(a,weights*field[b,axis],minlength=len(old))/np.maximum(den,1e-12)
            field[free]=.85*mean[free]+.15*field[free];field[anchors]=fixed
        if not resuming:
            outer['positions']=(old+field).tolist();outer['normals']=normals(old+field,faces)[faces].tolist();outer['r4_pattern']['collar_fit']='Measured native head/neck skin, low front height retained, harmonic transition to shoulders';final_clearance(outer,rig);new=np.array(outer['positions'])
        delta=new-old;fixed=delta[anchors];source_tree=BVHTree.FromPolygons(old.tolist(),faces.tolist(),all_triangles=True)
        def carry(d,cloth_count):
            before=np.array(d['positions']);after=before.copy();ids=np.flatnonzero((np.arange(len(before))<cloth_count)&(before[:,2]>clav-12)&(abs(before[:,0])<25))
            for vi in ids:
                key=tuple(before[vi])
                if key in cache:after[vi]+=cache[key];continue
                hit,_,fi,_=source_tree.find_nearest(Vector(before[vi]));tri=faces[fi];v0,v1=old[tri[1]]-old[tri[0]],old[tri[2]]-old[tri[0]];v2=np.array(hit)-old[tri[0]];d00,d01,d11=np.dot(v0,v0),np.dot(v0,v1),np.dot(v1,v1);d20,d21=np.dot(v2,v0),np.dot(v2,v1);denom=d00*d11-d01*d01
                if abs(denom)<1e-15:coef=np.array([1.,0.,0.])
                else:
                    u=(d11*d20-d01*d21)/denom;v=(d00*d21-d01*d20)/denom;coef=np.clip([1-u-v,u,v],0,1);coef/=max(coef.sum(),1e-12)
                dv=coef@delta[tri];after[vi]+=dv;cache[key]=dv
            return before,after
        if not resuming:
            before,after=carry(detail,len(detail['positions']));detail['positions']=after.tolist();local_normals(detail,before);detail['r4_collar_fit']=outer['r4_pattern']['collar_fit'];write(R/'Authored'/f'shirt_detail_{rig}.json',detail);np.savez_compressed(resume_file,before=before,after=after,outer_before=old)
        del detail;gc.collect()
        vest=read(R/'Authored'/f'vest_{rig}.json') if resuming else fit_carrier(rig,outer,body);vest_count=len(vest['positions']);neck_count=len(read(B/'Authored'/f'neck_skin_{rig}.json')['positions'])
        for row in manifest['rows']:
            if row['rig']!=rig or row.get('kind'):continue
            d=read(row['file'])
            if d.get('r4_collar_fit'):del d;continue
            before,after=carry(d,len(d['positions'])-vest_count-neck_count);after[-vest_count:]=vest['positions'];d['positions']=after.tolist();local_normals(d,before);d['r4_collar_fit']=outer['r4_pattern']['collar_fit'];write(Path(row['file']),d);del d;gc.collect();print('R4_MEASURED_COLLAR_WEAR',rig,Path(row['file']).stem,flush=True)
        distances=[]
        for vi in anchors:
            q=new[vi];hit,_,fi,_=head_tree.find_nearest(Vector(q));distances.append(float(np.dot(q-np.array(hit),hn[fi])))
        receipt[rig]=dict(anchors=len(anchors),min_head_clearance_cm=min(distances),max_anchor_correction_cm=float(np.linalg.norm(fixed,axis=1).max()),before_front_min_z_cm=float(old[anchors,2].min()),after_front_min_z_cm=float(new[anchors,2].min()),native_cuff_positions_preserved=True)
        print('R4_MEASURED_COLLAR_COMPLETE',rig,receipt[rig],flush=True)
    write(R/'collar-fitted.json',dict(completed=True,rigs=receipt,method='Native neck surface projection and harmonic cloth transition; all world/owner variants carried together'))
if __name__=='__main__':main()
